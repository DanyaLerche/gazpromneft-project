from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import schemas
from backend.models import Issue, User, Worklog
from backend.services import access_control

logger = logging.getLogger(__name__)


@dataclass
class IssueWorklogsResult:
    items: list[Worklog]
    total: int
    planned_hours: float | None
    logged_hours: float


@dataclass
class UserWorklogsResult:
    items: list[Worklog]
    total: int


def normalize_hours(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def to_worklog_schema(worklog: Worklog) -> schemas.Worklog:
    return schemas.Worklog(
        id=worklog.id,
        issue_id=worklog.issue_id,
        user_id=worklog.user_id,
        work_date=worklog.work_date,
        hours=normalize_hours(worklog.hours) or 0.0,
        comment=worklog.comment,
    )


def validate_period(date_from: date | None, date_to: date | None) -> None:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(status_code=400, detail="Invalid date range: 'from' must be <= 'to'")


def validate_hours(hours: float | Decimal | None) -> None:
    if hours is None:
        return
    if Decimal(str(hours)) <= 0:
        raise HTTPException(status_code=400, detail="hours must be > 0")


def ensure_patch_payload_not_empty(payload: dict) -> None:
    if not payload:
        raise HTTPException(status_code=400, detail="At least one field must be provided")


async def ensure_user_exists(session: AsyncSession, user_id: UUID) -> User:
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def ensure_issue_access(session: AsyncSession, issue_id: UUID, user_id: UUID) -> Issue:
    issue = (await session.execute(select(Issue).where(Issue.id == issue_id))).scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    await access_control.ensure_project_member_context(session, issue.project_id, user_id)
    return issue


async def _can_view_user_worklogs(session: AsyncSession, current_user_id: UUID, target_user_id: UUID) -> bool:
    return await access_control.can_manage_user_in_admin_scope(
        session,
        current_user_id,
        target_user_id,
    )


async def ensure_user_worklogs_access(session: AsyncSession, current_user_id: UUID, target_user_id: UUID) -> None:
    if not await _can_view_user_worklogs(session, current_user_id, target_user_id):
        raise HTTPException(status_code=403, detail="No access to user's worklogs")


async def ensure_can_modify_worklog(
    session: AsyncSession,
    worklog_user_id: UUID,
    issue_project_id: UUID,
    current_user_id: UUID,
) -> None:
    if worklog_user_id == current_user_id:
        return
    project_role = await access_control.resolve_project_role(
        session,
        issue_project_id,
        current_user_id,
    )
    if project_role == schemas.ProjectRole.ADMIN_PROJECT:
        return
    raise HTTPException(status_code=403, detail="No access to modify worklog")


async def create_issue_worklog(
    session: AsyncSession,
    issue_id: UUID,
    actor_id: UUID,
    payload: schemas.CreateWorklogRequest,
) -> Worklog:
    issue = await ensure_issue_access(session, issue_id, actor_id)
    validate_hours(payload.hours)

    worklog = Worklog(
        issue_id=issue.id,
        user_id=actor_id,
        work_date=payload.work_date,
        hours=Decimal(str(payload.hours)),
        comment=payload.comment,
    )
    session.add(worklog)
    await session.commit()
    await session.refresh(worklog)

    logger.info(
        "worklog_created issue_id=%s worklog_id=%s actor_id=%s",
        issue_id,
        worklog.id,
        actor_id,
    )
    return worklog


async def list_issue_worklogs(
    session: AsyncSession,
    issue_id: UUID,
    actor_id: UUID,
    date_from: date | None,
    date_to: date | None,
    limit: int,
    offset: int,
) -> IssueWorklogsResult:
    validate_period(date_from, date_to)
    issue = await ensure_issue_access(session, issue_id, actor_id)

    base_q = select(Worklog).where(Worklog.issue_id == issue_id)
    sum_q = select(func.coalesce(func.sum(Worklog.hours), 0)).where(Worklog.issue_id == issue_id)
    if date_from is not None:
        base_q = base_q.where(Worklog.work_date >= date_from)
        sum_q = sum_q.where(Worklog.work_date >= date_from)
    if date_to is not None:
        base_q = base_q.where(Worklog.work_date <= date_to)
        sum_q = sum_q.where(Worklog.work_date <= date_to)

    total = (await session.execute(select(func.count()).select_from(base_q.subquery()))).scalar_one()
    items = (
        await session.execute(
            base_q.order_by(Worklog.work_date.desc(), Worklog.id.desc()).offset(offset).limit(limit)
        )
    ).scalars().all()
    logged_hours_raw = (await session.execute(sum_q)).scalar_one()

    return IssueWorklogsResult(
        items=list(items),
        total=total,
        planned_hours=normalize_hours(issue.planned_hours),
        logged_hours=normalize_hours(logged_hours_raw) or 0.0,
    )


async def list_user_worklogs(
    session: AsyncSession,
    user_id: UUID,
    actor_id: UUID,
    project_id: UUID | None,
    date_from: date | None,
    date_to: date | None,
    limit: int,
    offset: int,
) -> UserWorklogsResult:
    validate_period(date_from, date_to)
    await ensure_user_exists(session, user_id)
    await ensure_user_worklogs_access(session, actor_id, user_id)

    if project_id is not None:
        await access_control.ensure_project_member_context(session, project_id, actor_id)

    base_q = select(Worklog).join(Issue, Issue.id == Worklog.issue_id).where(Worklog.user_id == user_id)
    if project_id is not None:
        base_q = base_q.where(Issue.project_id == project_id)
    if date_from is not None:
        base_q = base_q.where(Worklog.work_date >= date_from)
    if date_to is not None:
        base_q = base_q.where(Worklog.work_date <= date_to)

    total = (await session.execute(select(func.count()).select_from(base_q.subquery()))).scalar_one()
    items = (
        await session.execute(
            base_q.order_by(Worklog.work_date.desc(), Worklog.id.desc()).offset(offset).limit(limit)
        )
    ).scalars().all()
    return UserWorklogsResult(items=list(items), total=total)


async def get_worklog_for_update(session: AsyncSession, worklog_id: UUID) -> tuple[Worklog, Issue]:
    row = (
        await session.execute(
            select(Worklog, Issue)
            .join(Issue, Issue.id == Worklog.issue_id)
            .where(Worklog.id == worklog_id)
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Worklog not found")
    return row[0], row[1]


async def update_worklog(
    session: AsyncSession,
    worklog_id: UUID,
    actor_id: UUID,
    payload: schemas.UpdateWorklogRequest,
) -> Worklog:
    worklog, issue = await get_worklog_for_update(session, worklog_id)
    await ensure_can_modify_worklog(session, worklog.user_id, issue.project_id, actor_id)

    updates = payload.model_dump(exclude_unset=True)
    ensure_patch_payload_not_empty(updates)
    if "hours" in updates:
        validate_hours(updates["hours"])

    for field, value in updates.items():
        if field == "hours" and value is not None:
            setattr(worklog, field, Decimal(str(value)))
        else:
            setattr(worklog, field, value)

    await session.commit()
    await session.refresh(worklog)
    logger.info("worklog_updated worklog_id=%s actor_id=%s", worklog_id, actor_id)
    return worklog


async def delete_worklog(session: AsyncSession, worklog_id: UUID, actor_id: UUID) -> None:
    worklog, issue = await get_worklog_for_update(session, worklog_id)
    await ensure_can_modify_worklog(session, worklog.user_id, issue.project_id, actor_id)
    await session.delete(worklog)
    await session.commit()
    logger.info("worklog_deleted worklog_id=%s actor_id=%s", worklog_id, actor_id)
