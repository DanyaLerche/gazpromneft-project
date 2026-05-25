from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import exists, func, or_, select

from backend import schemas
from backend.api.dependencies import CurrentUser, Session
from backend.models import (
    Issue,
    IssueComment,
    IssueWatcher,
    Project,
    ProjectUser,
    Status,
    User,
    Worklog,
)
from backend.services import access_control

router = APIRouter(tags=["ForMe"])


def _normalize_hours(value) -> float | None:
    if value is None:
        return None
    return float(value)


async def _attach_logged_hours(session: Session, issues: list[Issue]) -> None:
    issue_ids = [issue.id for issue in issues]
    if not issue_ids:
        return

    rows = (
        await session.execute(
            select(
                Worklog.issue_id,
                func.coalesce(func.sum(Worklog.hours), 0).label("logged_hours"),
            )
            .where(Worklog.issue_id.in_(issue_ids))
            .group_by(Worklog.issue_id)
        )
    ).all()
    logged_hours_by_issue_id = {
        issue_id: _normalize_hours(logged_hours) or 0.0
        for issue_id, logged_hours in rows
    }
    for issue in issues:
        issue.logged_hours = logged_hours_by_issue_id.get(issue.id, 0.0)


def _status_to_schema(status: Status) -> schemas.Status:
    return schemas.Status(
        id=status.id,
        project_id=status.project_id,
        name=status.name,
        category=schemas.StatusCategory(status.category),
        sort_order=status.sort_order,
    )


def _project_to_schema(project: Project, role: schemas.ProjectRole) -> schemas.ProjectResponse:
    return schemas.ProjectResponse(
        id=project.id,
        key=project.key,
        name=project.name,
        description=project.description,
        category=schemas.ProjectCategory(project.category),
        created_by=project.created_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
        current_user_role=role,
    )


def _build_digest_items(
    issues: list[Issue],
    comments: list[IssueComment],
) -> list[schemas.ForMeDigestItem]:
    items: list[schemas.ForMeDigestItem] = []
    issue_by_id = {issue.id: issue for issue in issues}

    for issue in issues:
        items.append(
            schemas.ForMeDigestItem(
                item_type="issue_updated",
                issue_id=issue.id,
                issue_key=issue.key,
                issue_title=issue.title,
                project_id=issue.project_id,
                occurred_at=issue.updated_at,
                summary=f"Задача {issue.key} обновлена",
            )
        )

    for comment in comments:
        issue = issue_by_id.get(comment.issue_id)
        if issue is None:
            continue
        items.append(
            schemas.ForMeDigestItem(
                item_type="new_comment",
                issue_id=issue.id,
                issue_key=issue.key,
                issue_title=issue.title,
                project_id=issue.project_id,
                occurred_at=comment.created_at,
                summary=f"Новый комментарий в задаче {issue.key}",
            )
        )

    items.sort(key=lambda item: item.occurred_at, reverse=True)
    return items[:5]


def _build_action_history_items(
    created_issues: list[Issue],
    authored_comments: list[tuple[IssueComment, Issue]],
    authored_worklogs: list[tuple[Worklog, Issue]],
) -> list[schemas.ForMeActionHistoryItem]:
    items: list[schemas.ForMeActionHistoryItem] = []

    for issue in created_issues:
        items.append(
            schemas.ForMeActionHistoryItem(
                action_type="issue_created",
                issue_id=issue.id,
                issue_key=issue.key,
                issue_title=issue.title,
                project_id=issue.project_id,
                occurred_at=issue.created_at,
                summary=f"Создали задачу {issue.key}",
            )
        )

    for comment, issue in authored_comments:
        items.append(
            schemas.ForMeActionHistoryItem(
                action_type="comment_added",
                issue_id=issue.id,
                issue_key=issue.key,
                issue_title=issue.title,
                project_id=issue.project_id,
                occurred_at=comment.created_at,
                summary=f"Добавили комментарий к задаче {issue.key}",
            )
        )

    for worklog, issue in authored_worklogs:
        items.append(
            schemas.ForMeActionHistoryItem(
                action_type="worklog_added",
                issue_id=issue.id,
                issue_key=issue.key,
                issue_title=issue.title,
                project_id=issue.project_id,
                occurred_at=worklog.created_at,
                summary=f"Добавили запись времени по задаче {issue.key}",
            )
        )

    items.sort(key=lambda item: item.occurred_at, reverse=True)
    return items[:5]


@router.get("/for-me", response_model=schemas.ForMeResponse)
async def get_for_me(
    session: Session,
    current_user: CurrentUser,
    search: str | None = Query(None),
    project_id: UUID | None = None,
    status_id: UUID | None = None,
    sort: Literal["created_at", "updated_at", "due_date"] = Query("created_at"),
    last_seen_timestamp: datetime | None = Query(
        None,
        description="UTC-временная отметка последнего просмотра страницы /for-me",
    ),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """РђРіСЂРµРіРёСЂРѕРІР°РЅРЅС‹Рµ РґР°РЅРЅС‹Рµ СЃС‚СЂР°РЅРёС†С‹ "For Me"."""
    if project_id is not None:
        await access_control.ensure_project_access(
            session,
            project_id,
            current_user.id,
            current_user=current_user,
        )
        project_scope_ids = {project_id}
    else:
        project_scope_ids = await access_control.get_accessible_project_ids(
            session,
            current_user.id,
            current_user=current_user,
        )

    if not project_scope_ids:
        return schemas.ForMeResponse(
            issues=[],
            projects=[],
            total=0,
            filters=schemas.ForMeFilters(statuses=[], users=[]),
            mini_digest=schemas.ForMeDigest(
                last_seen_timestamp=last_seen_timestamp,
                generated_at=datetime.now(UTC),
                items=[],
            ),
            action_history=schemas.ForMeActionHistory(items=[]),
        )

    watcher_exists = exists(
        select(IssueWatcher.issue_id).where(
            IssueWatcher.issue_id == Issue.id,
            IssueWatcher.user_id == current_user.id,
        )
    )
    issues_query = (
        select(Issue)
        .where(
            Issue.project_id.in_(project_scope_ids),
            or_(
                Issue.assignee_id == current_user.id,
                Issue.author_id == current_user.id,
                watcher_exists,
            ),
        )
    )
    if search:
        pattern = f"%{search.strip()}%"
        issues_query = issues_query.where(or_(Issue.key.ilike(pattern), Issue.title.ilike(pattern)))
    if status_id is not None:
        issues_query = issues_query.where(Issue.status_id == status_id)

    issue_ids_subquery = issues_query.with_only_columns(Issue.id).subquery()

    sort_column = {
        "created_at": Issue.created_at,
        "updated_at": Issue.updated_at,
        "due_date": Issue.due_date,
    }[sort]
    issues_query = issues_query.order_by(sort_column.desc())

    total = (await session.execute(select(func.count()).select_from(issues_query.subquery()))).scalar_one()
    issues = (await session.execute(issues_query.offset(offset).limit(limit))).scalars().all()
    await _attach_logged_hours(session, issues)

    projects = (
        await session.execute(
            select(Project)
            .where(Project.id.in_(project_scope_ids))
            .order_by(Project.created_at.desc())
        )
    ).scalars().all()
    roles_by_project_id = await access_control.get_effective_project_roles(
        session,
        current_user.id,
        [project.id for project in projects],
        current_user=current_user,
    )

    statuses = (
        await session.execute(
            select(Status)
            .where(Status.project_id.in_(project_scope_ids))
            .order_by(Status.sort_order.asc())
        )
    ).scalars().all()

    user_ids_query = (
        select(ProjectUser.user_id).where(ProjectUser.project_id.in_(project_scope_ids))
        .union(select(Project.created_by).where(Project.id.in_(project_scope_ids)))
    )
    users = (
        await session.execute(
            select(User).where(User.id.in_(user_ids_query)).order_by(User.full_name.asc())
        )
    ).scalars().all()

    digest_issue_updates: list[Issue] = []
    digest_comments: list[IssueComment] = []
    if last_seen_timestamp is not None:
        digest_issue_updates = (
            await session.execute(
                select(Issue)
                .where(
                    Issue.id.in_(select(issue_ids_subquery.c.id)),
                    Issue.updated_at > last_seen_timestamp,
                )
                .order_by(Issue.updated_at.desc())
                .limit(20)
            )
        ).scalars().all()

        digest_comments = (
            await session.execute(
                select(IssueComment)
                .join(Issue, Issue.id == IssueComment.issue_id)
                .where(
                    Issue.id.in_(select(issue_ids_subquery.c.id)),
                    IssueComment.created_at > last_seen_timestamp,
                )
                .order_by(IssueComment.created_at.desc())
                .limit(20)
            )
        ).scalars().all()

    action_created_issues = (
        await session.execute(
            select(Issue)
            .where(
                Issue.project_id.in_(project_scope_ids),
                Issue.author_id == current_user.id,
            )
            .order_by(Issue.created_at.desc())
            .limit(5)
        )
    ).scalars().all()

    action_authored_comments = (
        await session.execute(
            select(IssueComment, Issue)
            .join(Issue, Issue.id == IssueComment.issue_id)
            .where(
                Issue.project_id.in_(project_scope_ids),
                IssueComment.author_id == current_user.id,
            )
            .order_by(IssueComment.created_at.desc())
            .limit(5)
        )
    ).all()

    action_authored_worklogs = (
        await session.execute(
            select(Worklog, Issue)
            .join(Issue, Issue.id == Worklog.issue_id)
            .where(
                Issue.project_id.in_(project_scope_ids),
                Worklog.user_id == current_user.id,
            )
            .order_by(Worklog.created_at.desc())
            .limit(5)
        )
    ).all()

    return schemas.ForMeResponse(
        issues=issues,
        projects=[
            _project_to_schema(project, roles_by_project_id[project.id])
            for project in projects
            if project.id in roles_by_project_id
        ],
        total=total,
        filters=schemas.ForMeFilters(
            statuses=[_status_to_schema(status) for status in statuses],
            users=users,
        ),
        mini_digest=schemas.ForMeDigest(
            last_seen_timestamp=last_seen_timestamp,
            generated_at=datetime.now(UTC),
            items=_build_digest_items(digest_issue_updates, digest_comments),
        ),
        action_history=schemas.ForMeActionHistory(
            items=_build_action_history_items(
                action_created_issues,
                action_authored_comments,
                action_authored_worklogs,
            )
        ),
    )
