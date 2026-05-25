from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError

from backend import schemas
from backend.api.dependencies import CurrentUser, Session
from backend.models import Issue, Status, Worklog
from backend.services import access_control

router = APIRouter(tags=["Issues"])


async def _get_issue_or_404(session: Session, issue_id: UUID) -> Issue:
    issue = (await session.execute(select(Issue).where(Issue.id == issue_id))).scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=404, detail="Р—Р°РґР°С‡Р° РЅРµ РЅР°Р№РґРµРЅР°")
    return issue


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


async def _get_issue_in_project(
    session: Session,
    project_id: UUID,
    issue_id: UUID,
) -> Issue | None:
    return (
        await session.execute(
            select(Issue).where(
                Issue.id == issue_id,
                Issue.project_id == project_id,
            )
        )
    ).scalar_one_or_none()


async def _validate_parent_issue(
    session: Session,
    *,
    project_id: UUID,
    child_type: str,
    parent_id: UUID | None,
    current_issue_id: UUID | None = None,
) -> UUID | None:
    if parent_id is None:
        return None

    if child_type != schemas.IssueType.TASK.value:
        raise HTTPException(status_code=400, detail="Родительская связь доступна только для задач")

    parent_issue = await _get_issue_in_project(session, project_id, parent_id)
    if parent_issue is None:
        raise HTTPException(
            status_code=400,
            detail="Родительская задача не найдена в рамках проекта",
        )

    if current_issue_id is None:
        return parent_issue.id

    if parent_issue.id == current_issue_id:
        raise HTTPException(status_code=400, detail="Задача не может быть родителем самой себе")

    visited_ids = {parent_issue.id}
    cursor = parent_issue
    while cursor.parent_id is not None:
        if cursor.parent_id == current_issue_id:
            raise HTTPException(status_code=400, detail="Циклическая иерархия задач запрещена")
        if cursor.parent_id in visited_ids:
            break
        visited_ids.add(cursor.parent_id)
        next_parent = await _get_issue_in_project(session, project_id, cursor.parent_id)
        if next_parent is None:
            break
        cursor = next_parent

    return parent_issue.id


async def _generate_issue_key(session: Session, project_id: UUID, project_key: str) -> str:
    """Р“РµРЅРµСЂРёСЂСѓРµС‚ РєР»СЋС‡ Р·Р°РґР°С‡Рё: PAY-1, PAY-2, ..."""
    result = await session.execute(
        select(func.count()).select_from(Issue).where(Issue.project_id == project_id)
    )
    next_number = result.scalar_one() + 1
    return f"{project_key}-{next_number}"


async def _acquire_issue_key_lock(session: Session, project_id: UUID) -> None:
    """РЎРµСЂРёР°Р»РёР·СѓРµС‚ РіРµРЅРµСЂР°С†РёСЋ РєР»СЋС‡Р° Р·Р°РґР°С‡ РІ СЂР°РјРєР°С… РїСЂРѕРµРєС‚Р°."""
    await session.execute(select(func.pg_advisory_xact_lock(func.hashtext(str(project_id)))))


@router.get("/projects/{project_id}/issues", response_model=schemas.PagedIssues)
async def list_issues(
    project_id: UUID,
    session: Session,
    current_user: CurrentUser,
    type: schemas.IssueType | None = Query(None, description="epic РёР»Рё task"),
    status_id: UUID | None = None,
    assignee_id: UUID | None = None,
    author_id: UUID | None = None,
    parent_id: UUID | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    taken_in_work_from: datetime | None = None,
    taken_in_work_to: datetime | None = None,
    resolved_from: datetime | None = None,
    resolved_to: datetime | None = None,
    q: str | None = Query(None, max_length=200),
    sort: str = Query("created_at", enum=["created_at", "taken_in_work_at", "resolved_at", "due_date"]),
    order: str = Query("desc", enum=["asc", "desc"]),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """РЎРїРёСЃРѕРє Р·Р°РґР°С‡/СЌРїРёРєРѕРІ СЃ С„РёР»СЊС‚СЂР°РјРё."""
    await access_control.ensure_project_access(
        session,
        project_id,
        current_user.id,
        current_user=current_user,
    )

    query = select(Issue).where(Issue.project_id == project_id)
    filters = []

    if type is not None:
        filters.append(Issue.type == type.value)
    if status_id is not None:
        filters.append(Issue.status_id == status_id)
    if assignee_id is not None:
        filters.append(Issue.assignee_id == assignee_id)
    if author_id is not None:
        filters.append(Issue.author_id == author_id)
    if parent_id is not None:
        filters.append(Issue.parent_id == parent_id)
    if q:
        filters.append(or_(Issue.key.ilike(f"%{q}%"), Issue.title.ilike(f"%{q}%")))
    if created_from is not None:
        filters.append(Issue.created_at >= created_from)
    if created_to is not None:
        filters.append(Issue.created_at <= created_to)
    if taken_in_work_from is not None:
        filters.append(Issue.taken_in_work_at >= taken_in_work_from)
    if taken_in_work_to is not None:
        filters.append(Issue.taken_in_work_at <= taken_in_work_to)
    if resolved_from is not None:
        filters.append(Issue.resolved_at >= resolved_from)
    if resolved_to is not None:
        filters.append(Issue.resolved_at <= resolved_to)

    if filters:
        query = query.where(and_(*filters))

    total = (await session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    order_column = getattr(Issue, sort, Issue.created_at)
    query = query.order_by(order_column.desc() if order == "desc" else order_column.asc())
    items = (await session.execute(query.offset(offset).limit(limit))).scalars().all()
    await _attach_logged_hours(session, items)
    return schemas.PagedIssues(items=items, total=total)


@router.post("/projects/{project_id}/issues", status_code=201, response_model=schemas.IssueResponse)
async def create_issue(
    project_id: UUID,
    body: schemas.CreateIssueRequest,
    session: Session,
    current_user: CurrentUser,
):
    """РЎРѕР·РґР°С‚СЊ Р·Р°РґР°С‡Сѓ/СЌРїРёРє. РљР»СЋС‡ РіРµРЅРµСЂРёСЂСѓРµС‚СЃСЏ Р±СЌРєРµРЅРґРѕРј.

    Source of truth for onboarding signals/scoring:
    backend/docs/onboarding_signals.md
    """
    project = await access_control.ensure_project_access(
        session,
        project_id,
        current_user.id,
        current_user=current_user,
    )

    status = (
        await session.execute(
            select(Status).where(
                Status.id == body.status_id,
                Status.project_id == project_id,
            )
        )
    ).scalar_one_or_none()
    if not status:
        raise HTTPException(status_code=400, detail="РЎС‚Р°С‚СѓСЃ РЅРµ РЅР°Р№РґРµРЅ РёР»Рё РЅРµ РїСЂРёРЅР°РґР»РµР¶РёС‚ РїСЂРѕРµРєС‚Сѓ")

    normalized_parent_id = await _validate_parent_issue(
        session,
        project_id=project_id,
        child_type=body.type.value,
        parent_id=body.parent_id,
    )

    try:
        await _acquire_issue_key_lock(session, project_id)
        key = await _generate_issue_key(session, project_id, project.key)
        issue = Issue(
            project_id=project_id,
            key=key,
            type=body.type.value,
            title=body.title,
            description=body.description,
            status_id=body.status_id,
            criticality_id=body.criticality_id,
            author_id=current_user.id,
            assignee_id=body.assignee_id,
            parent_id=normalized_parent_id,
            start_date=body.start_date,
            due_date=body.due_date,
            planned_hours=body.planned_hours,
        )
        session.add(issue)
        await session.commit()
        await session.refresh(issue)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="РљРѕРЅС„Р»РёРєС‚ РґР°РЅРЅС‹С…")
    return {"issue": issue}


@router.get("/projects/{project_id}/issues/by-key/{issue_key}", response_model=schemas.IssueResponse)
async def get_issue_by_key(
    project_id: UUID,
    issue_key: str,
    session: Session,
    current_user: CurrentUser,
):
    """РџРѕР»СѓС‡РёС‚СЊ Р·Р°РґР°С‡Сѓ РїРѕ РєР»СЋС‡Сѓ (РЅР°РїСЂРёРјРµСЂ PAY-123)."""
    await access_control.ensure_project_access(
        session,
        project_id,
        current_user.id,
        current_user=current_user,
    )
    issue = (
        await session.execute(
            select(Issue).where(
                Issue.project_id == project_id,
                Issue.key == issue_key,
            )
        )
    ).scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=404, detail="Р—Р°РґР°С‡Р° РЅРµ РЅР°Р№РґРµРЅР°")
    return {"issue": issue}


@router.get("/issues/{issue_id}", response_model=schemas.IssueDetailsResponse)
async def get_issue(
    issue_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    """Р”РµС‚Р°Р»СЊРЅР°СЏ РєР°СЂС‚РѕС‡РєР° Р·Р°РґР°С‡Рё."""
    issue = await _get_issue_or_404(session, issue_id)
    await access_control.ensure_project_access(
        session,
        issue.project_id,
        current_user.id,
        current_user=current_user,
    )
    await _attach_logged_hours(session, [issue])
    return schemas.IssueDetailsResponse(
        issue=issue,
        watchers=[],
        comments=[],
        attachments=[],
        worklog_summary=schemas.WorklogSummary(
            planned_hours=_normalize_hours(issue.planned_hours),
            logged_hours=issue.logged_hours or 0.0,
        ),
    )


@router.patch("/issues/{issue_id}", response_model=schemas.IssueResponse)
async def update_issue(
    issue_id: UUID,
    body: schemas.UpdateIssueRequest,
    session: Session,
    current_user: CurrentUser,
):
    """РћР±РЅРѕРІРёС‚СЊ Р·Р°РґР°С‡Сѓ (С‡Р°СЃС‚РёС‡РЅРѕ)."""
    issue = await _get_issue_or_404(session, issue_id)
    await access_control.ensure_project_access(
        session,
        issue.project_id,
        current_user.id,
        current_user=current_user,
    )

    updates = body.model_dump(exclude_unset=True)
    if "status_id" in updates:
        status = (
            await session.execute(
                select(Status).where(
                    Status.id == updates["status_id"],
                    Status.project_id == issue.project_id,
                )
            )
        ).scalar_one_or_none()
        if not status:
            raise HTTPException(status_code=400, detail="РЎС‚Р°С‚СѓСЃ РЅРµ РЅР°Р№РґРµРЅ")

    if "parent_id" in updates:
        updates["parent_id"] = await _validate_parent_issue(
            session,
            project_id=issue.project_id,
            child_type=issue.type,
            parent_id=updates["parent_id"],
            current_issue_id=issue.id,
        )

    for field, value in updates.items():
        setattr(issue, field, value)

    await session.commit()
    await session.refresh(issue)
    return {"issue": issue}


@router.delete("/issues/{issue_id}", status_code=204)
async def delete_issue(
    issue_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    """РЈРґР°Р»РёС‚СЊ Р·Р°РґР°С‡Сѓ. РўСЂРµР±СѓРµС‚ admin_project."""
    issue = await _get_issue_or_404(session, issue_id)
    await access_control.ensure_project_admin_context(
        session,
        issue.project_id,
        current_user.id,
        current_user=current_user,
    )

    await session.delete(issue)
    await session.commit()
