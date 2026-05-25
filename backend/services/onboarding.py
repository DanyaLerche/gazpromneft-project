from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import case, func, literal, select, union, union_all
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import (
    Criticality,
    Issue,
    IssueComment,
    IssueWatcher,
    Project,
    ProjectUser,
    User,
    WikiPage,
    WikiPageAttachment,
    WikiPageRevision,
    OnboardingRecommendationSnapshot,
    Worklog,
)
from backend.services import access_control

READS_TOP_N_DEFAULT = 7
ISSUES_TOP_N_DEFAULT = 7
KEY_PEOPLE_TOP_N_DEFAULT = 5
PEOPLE_DOMAIN_COUNT = 4
ONBOARDING_CACHE_TTL_HOURS = 24


@dataclass(slots=True)
class OnboardingListItem:
    id: UUID
    title: str
    reason: str
    score: float | None = None


@dataclass(slots=True)
class OnboardingPersonItem:
    id: UUID
    full_name: str
    reason: str
    email: str | None = None
    score: float | None = None


@dataclass(slots=True)
class OnboardingRecommendations:
    reads: list[OnboardingListItem] = field(default_factory=list)
    issues_to_review: list[OnboardingListItem] = field(default_factory=list)
    key_people: list[OnboardingPersonItem] = field(default_factory=list)


@dataclass(slots=True)
class OnboardingRecommendationsResult:
    recommendations: OnboardingRecommendations
    generated_at: datetime
    cached: bool


def _resolve_actor(current_user: User | UUID) -> tuple[UUID, User | None]:
    if isinstance(current_user, User):
        return current_user.id, current_user
    return current_user, None


def _freshness_score(updated_at: datetime, now: datetime) -> float:
    days = max(0, (now - updated_at).days)
    return max(0.0, 1.0 - (days / 30.0))


def _safe_ratio(value: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return max(0.0, min(1.0, value / denominator))


def _build_reads_items(
    rows: list[dict[str, Any]],
    *,
    now: datetime,
    limit: int,
) -> list[OnboardingListItem]:
    items: list[tuple[float, datetime, UUID, OnboardingListItem]] = []
    for row in rows:
        updated_at: datetime = row["updated_at"]
        version = int(row["version"] or 1)
        revisions_count = int(row["revisions_count"] or 0)
        attachments_count = int(row["attachments_count"] or 0)

        freshness = _freshness_score(updated_at, now)
        update_frequency = _safe_ratio(float(version), 10.0)
        revision_density = _safe_ratio(float(revisions_count), 10.0)
        attachments_signal = _safe_ratio(float(attachments_count), 5.0)

        score = 100.0 * (
            0.35 * freshness
            + 0.25 * update_frequency
            + 0.20 * revision_density
            + 0.20 * attachments_signal
        )
        score = round(score, 2)

        reason_bits = [f"обновлена {updated_at.date().isoformat()}"]
        if revisions_count > 0:
            reason_bits.append(f"{revisions_count} ревизий")
        if attachments_count > 0:
            reason_bits.append(f"{attachments_count} вложений")
        if version > 1:
            reason_bits.append(f"версия {version}")
        reason = ", ".join(reason_bits)
        items.append(
            (
                score,
                updated_at,
                row["id"],
                OnboardingListItem(
                    id=row["id"],
                    title=row["title"],
                    reason=reason,
                    score=score,
                ),
            )
        )

    items.sort(key=lambda x: (-x[0], -x[1].timestamp(), str(x[2])))
    return [payload for _, _, _, payload in items[:limit]]


def _build_issues_items(
    rows: list[dict[str, Any]],
    *,
    now: datetime,
    limit: int,
) -> list[OnboardingListItem]:
    items: list[tuple[float, datetime, UUID, OnboardingListItem]] = []
    for row in rows:
        updated_at: datetime = row["updated_at"]
        comments_count = int(row["comments_count"] or 0)
        worklogs_count = int(row["worklogs_count"] or 0)
        watchers_count = int(row["watchers_count"] or 0)
        activity_raw = comments_count + worklogs_count + watchers_count

        criticality_level = int(row["criticality_level"] or 1)
        criticality_signal = _safe_ratio(float(criticality_level), 5.0)
        activity_signal = _safe_ratio(float(activity_raw), 20.0)
        freshness = _freshness_score(updated_at, now)
        children_count = int(row.get("children_count") or 0)
        issue_type = str(row.get("type") or "task")
        epic_link_signal = 0.3
        if issue_type == "epic" and children_count > 0:
            epic_link_signal = 1.0
        elif row["parent_id"] is not None:
            epic_link_signal = 0.7

        score = 100.0 * (
            0.30 * activity_signal
            + 0.30 * criticality_signal
            + 0.20 * freshness
            + 0.20 * epic_link_signal
        )
        score = round(score, 2)

        reason_bits: list[str] = []
        criticality_name = row.get("criticality_name")
        if criticality_name:
            reason_bits.append(f"критичность {criticality_name.lower()}")
        if comments_count > 0:
            reason_bits.append(f"{comments_count} комментариев")
        if worklogs_count > 0:
            reason_bits.append(f"{worklogs_count} записей времени")
        if watchers_count > 0:
            reason_bits.append(f"{watchers_count} наблюдателей")
        if issue_type == "epic" and children_count > 0:
            reason_bits.append(f"{children_count} дочерних задач")
        elif row["parent_id"] is not None:
            reason_bits.append("связана с эпиком")
        reason_bits.append(f"обновлена {updated_at.date().isoformat()}")
        reason = ", ".join(reason_bits)
        items.append(
            (
                score,
                updated_at,
                row["id"],
                OnboardingListItem(
                    id=row["id"],
                    title=f"{row['key']} · {row['title']}",
                    reason=reason,
                    score=score,
                ),
            )
        )

    items.sort(key=lambda x: (-x[0], -x[1].timestamp(), str(x[2])))
    return [payload for _, _, _, payload in items[:limit]]


def _build_people_items(
    rows: list[dict[str, Any]],
    *,
    limit: int,
) -> list[OnboardingPersonItem]:
    if not rows:
        return []

    max_activity = max(int(row["activity_count"] or 0) for row in rows)
    items: list[tuple[float, int, str, OnboardingPersonItem]] = []
    for row in rows:
        activity_count = int(row["activity_count"] or 0)
        domain_count = int(row["domain_count"] or 0)
        is_project_admin = bool(row["is_project_admin"])
        is_project_creator = bool(row["is_project_creator"])

        if is_project_admin:
            role_signal = 1.0
        elif is_project_creator:
            role_signal = 0.8
        else:
            role_signal = 0.5

        activity_signal = _safe_ratio(float(activity_count), float(max_activity))
        cross_domain_signal = _safe_ratio(float(domain_count), float(PEOPLE_DOMAIN_COUNT))

        score = 100.0 * (
            0.35 * role_signal
            + 0.45 * activity_signal
            + 0.20 * cross_domain_signal
        )
        score = round(score, 2)

        role_bits: list[str] = []
        if is_project_admin:
            role_bits.append("project_admin")
        if is_project_creator:
            role_bits.append("project_creator")
        if not role_bits:
            role_bits.append("active_contributor")

        role_labels = {
            "project_admin": "администратор проекта",
            "project_creator": "создатель проекта",
            "active_contributor": "активный участник",
        }
        reason_bits = [", ".join(role_labels.get(role, role) for role in role_bits)]
        if activity_count > 0:
            reason_bits.append(f"{activity_count} действий в проекте")
        if domain_count > 0:
            reason_bits.append(f"активен в {domain_count} зонах проекта")
        reason = ", ".join(reason_bits)
        item = OnboardingPersonItem(
            id=row["id"],
            full_name=row["full_name"],
            email=row.get("email"),
            reason=reason,
            score=score,
        )
        items.append((score, activity_count, row["full_name"], item))

    items.sort(key=lambda x: (-x[0], -x[1], x[2]))
    return [payload for _, _, _, payload in items[:limit]]


async def build_onboarding_recommendations(
    session: AsyncSession,
    project_id: UUID,
    current_user: User | UUID,
    *,
    reads_limit: int = READS_TOP_N_DEFAULT,
    issues_limit: int = ISSUES_TOP_N_DEFAULT,
    key_people_limit: int = KEY_PEOPLE_TOP_N_DEFAULT,
) -> OnboardingRecommendations:
    now = datetime.now(UTC)
    actor_id, _ = _resolve_actor(current_user)

    revisions_sq = (
        select(
            WikiPageRevision.page_id.label("page_id"),
            func.count(WikiPageRevision.id).label("revisions_count"),
        )
        .where(WikiPageRevision.project_id == project_id)
        .group_by(WikiPageRevision.page_id)
        .subquery()
    )
    attachments_sq = (
        select(
            WikiPageAttachment.page_id.label("page_id"),
            func.count(WikiPageAttachment.id).label("attachments_count"),
        )
        .select_from(WikiPageAttachment)
        .join(WikiPage, WikiPage.id == WikiPageAttachment.page_id)
        .where(WikiPage.project_id == project_id)
        .group_by(WikiPageAttachment.page_id)
        .subquery()
    )
    reads_stmt = (
        select(
            WikiPage.id,
            WikiPage.title,
            WikiPage.version,
            WikiPage.updated_at,
            func.coalesce(revisions_sq.c.revisions_count, 0).label("revisions_count"),
            func.coalesce(attachments_sq.c.attachments_count, 0).label("attachments_count"),
        )
        .select_from(WikiPage)
        .outerjoin(revisions_sq, revisions_sq.c.page_id == WikiPage.id)
        .outerjoin(attachments_sq, attachments_sq.c.page_id == WikiPage.id)
        .where(WikiPage.project_id == project_id)
        .order_by(WikiPage.updated_at.desc(), WikiPage.id.asc())
        .limit(max(reads_limit * 4, reads_limit))
    )
    reads_rows = [dict(row._mapping) for row in (await session.execute(reads_stmt)).all()]
    reads = _build_reads_items(reads_rows, now=now, limit=reads_limit)

    comments_sq = (
        select(
            IssueComment.issue_id.label("issue_id"),
            func.count(IssueComment.id).label("comments_count"),
        )
        .select_from(IssueComment)
        .join(Issue, Issue.id == IssueComment.issue_id)
        .where(Issue.project_id == project_id)
        .group_by(IssueComment.issue_id)
        .subquery()
    )
    watchers_sq = (
        select(
            IssueWatcher.issue_id.label("issue_id"),
            func.count(IssueWatcher.user_id).label("watchers_count"),
        )
        .select_from(IssueWatcher)
        .join(Issue, Issue.id == IssueWatcher.issue_id)
        .where(Issue.project_id == project_id)
        .group_by(IssueWatcher.issue_id)
        .subquery()
    )
    worklogs_sq = (
        select(
            Worklog.issue_id.label("issue_id"),
            func.count(Worklog.id).label("worklogs_count"),
        )
        .select_from(Worklog)
        .join(Issue, Issue.id == Worklog.issue_id)
        .where(Issue.project_id == project_id)
        .group_by(Worklog.issue_id)
        .subquery()
    )
    child_issues = Issue.__table__.alias("child_issues")
    issues_stmt = (
        select(
            Issue.id,
            Issue.key,
            Issue.type,
            Issue.title,
            Issue.parent_id,
            Issue.updated_at,
            Criticality.level.label("criticality_level"),
            Criticality.name.label("criticality_name"),
            func.coalesce(comments_sq.c.comments_count, 0).label("comments_count"),
            func.coalesce(worklogs_sq.c.worklogs_count, 0).label("worklogs_count"),
            func.coalesce(watchers_sq.c.watchers_count, 0).label("watchers_count"),
            (
                select(func.count())
                .select_from(child_issues)
                .where(child_issues.c.parent_id == Issue.id)
                .scalar_subquery()
            ).label("children_count"),
        )
        .select_from(Issue)
        .outerjoin(Criticality, Criticality.id == Issue.criticality_id)
        .outerjoin(comments_sq, comments_sq.c.issue_id == Issue.id)
        .outerjoin(worklogs_sq, worklogs_sq.c.issue_id == Issue.id)
        .outerjoin(watchers_sq, watchers_sq.c.issue_id == Issue.id)
        .where(Issue.project_id == project_id)
        .order_by(Issue.updated_at.desc(), Issue.id.asc())
        .limit(max(issues_limit * 6, issues_limit))
    )
    issues_rows = [dict(row._mapping) for row in (await session.execute(issues_stmt)).all()]
    issues_to_review = _build_issues_items(issues_rows, now=now, limit=issues_limit)

    creator_id = (
        await session.execute(select(Project.created_by).where(Project.id == project_id))
    ).scalar_one_or_none()

    project_admins_sq = (
        select(
            ProjectUser.user_id.label("user_id"),
            func.max(
                case(
                    (ProjectUser.role == "admin_project", 1),
                    else_=0,
                )
            ).label("is_project_admin"),
        )
        .where(ProjectUser.project_id == project_id)
        .group_by(ProjectUser.user_id)
        .subquery()
    )

    user_events = union_all(
        select(Issue.author_id.label("user_id"), literal("issues").label("domain")).where(
            Issue.project_id == project_id
        ),
        select(Issue.assignee_id.label("user_id"), literal("issues").label("domain")).where(
            Issue.project_id == project_id,
            Issue.assignee_id.is_not(None),
        ),
        select(IssueComment.author_id.label("user_id"), literal("comments").label("domain"))
        .select_from(IssueComment)
        .join(Issue, Issue.id == IssueComment.issue_id)
        .where(Issue.project_id == project_id),
        select(Worklog.user_id.label("user_id"), literal("worklogs").label("domain"))
        .select_from(Worklog)
        .join(Issue, Issue.id == Worklog.issue_id)
        .where(Issue.project_id == project_id),
        select(WikiPage.updated_by.label("user_id"), literal("wiki").label("domain")).where(
            WikiPage.project_id == project_id
        ),
        select(WikiPageRevision.created_by.label("user_id"), literal("wiki").label("domain")).where(
            WikiPageRevision.project_id == project_id
        ),
    ).subquery()

    user_activity_sq = (
        select(
            user_events.c.user_id.label("user_id"),
            func.count().label("activity_count"),
            func.count(func.distinct(user_events.c.domain)).label("domain_count"),
        )
        .group_by(user_events.c.user_id)
        .subquery()
    )

    candidate_selects = [
        select(project_admins_sq.c.user_id.label("user_id")),
        select(user_activity_sq.c.user_id.label("user_id")),
    ]
    if creator_id is not None:
        candidate_selects.append(select(literal(creator_id).label("user_id")))

    candidate_ids_sq = union(*candidate_selects).subquery()

    people_stmt = (
        select(
            User.id,
            User.full_name,
            User.email,
            func.coalesce(project_admins_sq.c.is_project_admin, 0).label("is_project_admin"),
            case((User.id == creator_id, 1), else_=0).label("is_project_creator"),
            func.coalesce(user_activity_sq.c.activity_count, 0).label("activity_count"),
            func.coalesce(user_activity_sq.c.domain_count, 0).label("domain_count"),
        )
        .select_from(User)
        .join(candidate_ids_sq, candidate_ids_sq.c.user_id == User.id)
        .outerjoin(project_admins_sq, project_admins_sq.c.user_id == User.id)
        .outerjoin(user_activity_sq, user_activity_sq.c.user_id == User.id)
        .where(
            User.id != actor_id,
            User.is_active.is_(True),
        )
        .order_by(
            func.coalesce(user_activity_sq.c.activity_count, 0).desc(),
            User.full_name.asc(),
        )
        .limit(max(key_people_limit * 6, key_people_limit))
    )
    people_rows = [dict(row._mapping) for row in (await session.execute(people_stmt)).all()]
    key_people = _build_people_items(people_rows, limit=key_people_limit)

    return OnboardingRecommendations(
        reads=reads,
        issues_to_review=issues_to_review,
        key_people=key_people,
    )


def _serialize_recommendations_payload(recommendations: OnboardingRecommendations) -> dict[str, Any]:
    return {
        "reads": [
            {
                "id": str(item.id),
                "title": item.title,
                "reason": item.reason,
                "score": item.score,
            }
            for item in recommendations.reads
        ],
        "issues_to_review": [
            {
                "id": str(item.id),
                "title": item.title,
                "reason": item.reason,
                "score": item.score,
            }
            for item in recommendations.issues_to_review
        ],
        "key_people": [
            {
                "id": str(item.id),
                "full_name": item.full_name,
                "email": item.email,
                "reason": item.reason,
                "score": item.score,
            }
            for item in recommendations.key_people
        ],
    }


def _deserialize_recommendations_payload(payload: dict[str, Any]) -> OnboardingRecommendations:
    reads = [
        OnboardingListItem(
            id=UUID(item["id"]),
            title=item["title"],
            reason=item["reason"],
            score=item.get("score"),
        )
        for item in payload.get("reads", [])
    ]
    issues_to_review = [
        OnboardingListItem(
            id=UUID(item["id"]),
            title=item["title"],
            reason=item["reason"],
            score=item.get("score"),
        )
        for item in payload.get("issues_to_review", [])
    ]
    key_people = [
        OnboardingPersonItem(
            id=UUID(item["id"]),
            full_name=item["full_name"],
            email=item.get("email"),
            reason=item["reason"],
            score=item.get("score"),
        )
        for item in payload.get("key_people", [])
    ]
    return OnboardingRecommendations(
        reads=reads,
        issues_to_review=issues_to_review,
        key_people=key_people,
    )


async def get_or_compute_onboarding_recommendations(
    session: AsyncSession,
    project_id: UUID,
    current_user: User | UUID,
    *,
    force: bool = False,
    reads_limit: int = READS_TOP_N_DEFAULT,
    issues_limit: int = ISSUES_TOP_N_DEFAULT,
    key_people_limit: int = KEY_PEOPLE_TOP_N_DEFAULT,
    ttl_hours: int = ONBOARDING_CACHE_TTL_HOURS,
) -> OnboardingRecommendationsResult:
    actor_id, actor_obj = _resolve_actor(current_user)
    await access_control.ensure_project_access(
        session,
        project_id,
        actor_id,
        current_user=actor_obj,
    )

    now = datetime.now(UTC)
    if not force:
        cached_snapshot = (
            await session.execute(
                select(OnboardingRecommendationSnapshot).where(
                    OnboardingRecommendationSnapshot.project_id == project_id,
                    OnboardingRecommendationSnapshot.user_id == actor_id,
                    OnboardingRecommendationSnapshot.expires_at > now,
                )
            )
        ).scalar_one_or_none()
        if cached_snapshot is not None:
            return OnboardingRecommendationsResult(
                recommendations=_deserialize_recommendations_payload(cached_snapshot.payload),
                generated_at=cached_snapshot.generated_at,
                cached=True,
            )

    recommendations = await build_onboarding_recommendations(
        session,
        project_id,
        actor_id,
        reads_limit=reads_limit,
        issues_limit=issues_limit,
        key_people_limit=key_people_limit,
    )
    generated_at = datetime.now(UTC)
    expires_at = generated_at + timedelta(hours=max(ttl_hours, 1))
    payload = _serialize_recommendations_payload(recommendations)

    snapshot_insert = (
        insert(OnboardingRecommendationSnapshot)
        .values(
            id=uuid4(),
            project_id=project_id,
            user_id=actor_id,
            payload=payload,
            generated_at=generated_at,
            expires_at=expires_at,
        )
        .on_conflict_do_update(
            index_elements=["project_id", "user_id"],
            set_={
                "payload": payload,
                "generated_at": generated_at,
                "expires_at": expires_at,
                "updated_at": func.now(),
            },
        )
    )
    await session.execute(snapshot_insert)
    await session.commit()

    return OnboardingRecommendationsResult(
        recommendations=recommendations,
        generated_at=generated_at,
        cached=False,
    )
