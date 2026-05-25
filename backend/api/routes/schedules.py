from __future__ import annotations

from datetime import UTC, date, datetime, time
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from backend import schemas
from backend.api.dependencies import CurrentUser, Session
from backend.models import ProjectUser, Schedule, User
from backend.services import access_control

router = APIRouter(tags=["Schedules"])


def _normalize_hours(value: Decimal | float | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _schedule_to_schema(schedule: Schedule) -> schemas.Schedule:
    derived_timestamp = datetime.combine(schedule.date, time.min, tzinfo=UTC)
    return schemas.Schedule(
        id=schedule.id,
        user_id=schedule.user_id,
        date=schedule.date,
        planned_hours=_normalize_hours(schedule.planned_hours),
        comment=schedule.comment,
        created_at=derived_timestamp,
        updated_at=derived_timestamp,
    )


def _user_lite_to_schema(user: User) -> schemas.UserLite:
    return schemas.UserLite(
        id=user.id,
        full_name=user.full_name,
    )


async def _get_user_or_404(session: Session, user_id: UUID) -> User:
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def _get_schedule_or_404(session: Session, schedule_id: UUID) -> Schedule:
    schedule = (await session.execute(select(Schedule).where(Schedule.id == schedule_id))).scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


async def _require_schedule_access(
    session: Session,
    current_user: User,
    target_user_id: UUID,
) -> None:
    await access_control.ensure_can_manage_user_in_admin_scope(
        session,
        current_user.id,
        target_user_id,
        current_user=current_user,
    )


def _validate_period(date_from: date | None, date_to: date | None) -> None:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(status_code=400, detail="Invalid date range: 'from' must be <= 'to'")


@router.get("/users/{user_id}/schedules", response_model=schemas.PagedSchedules)
async def list_user_schedules(
    user_id: UUID,
    session: Session,
    current_user: CurrentUser,
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List schedules for one user."""
    _validate_period(date_from, date_to)
    await _get_user_or_404(session, user_id)
    await _require_schedule_access(session, current_user, user_id)

    query = select(Schedule).where(Schedule.user_id == user_id)
    if date_from is not None:
        query = query.where(Schedule.date >= date_from)
    if date_to is not None:
        query = query.where(Schedule.date <= date_to)

    total = (await session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    schedules = (
        await session.execute(query.order_by(Schedule.date.desc()).offset(offset).limit(limit))
    ).scalars().all()
    return schemas.PagedSchedules(
        items=[_schedule_to_schema(schedule) for schedule in schedules],
        total=total,
    )


@router.post("/users/{user_id}/schedules", status_code=201, response_model=schemas.ScheduleResponse)
async def create_schedule(
    user_id: UUID,
    body: schemas.CreateScheduleRequest,
    session: Session,
    current_user: CurrentUser,
):
    """Create one schedule row for user/date."""
    await _get_user_or_404(session, user_id)
    await _require_schedule_access(session, current_user, user_id)

    existing = (
        await session.execute(
            select(Schedule).where(
                Schedule.user_id == user_id,
                Schedule.date == body.date,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Schedule for this date already exists")

    schedule = Schedule(
        user_id=user_id,
        date=body.date,
        planned_hours=body.planned_hours,
        comment=body.comment,
    )
    session.add(schedule)
    await session.commit()
    await session.refresh(schedule)
    return {"schedule": _schedule_to_schema(schedule)}


@router.patch("/schedules/{schedule_id}", response_model=schemas.ScheduleResponse)
async def update_schedule(
    schedule_id: UUID,
    body: schemas.UpdateScheduleRequest,
    session: Session,
    current_user: CurrentUser,
):
    """Update planned_hours/comment for schedule row."""
    schedule = await _get_schedule_or_404(session, schedule_id)
    await _require_schedule_access(session, current_user, schedule.user_id)

    updates = body.model_dump(exclude_unset=True)
    if "planned_hours" in updates:
        schedule.planned_hours = updates["planned_hours"]
    if "comment" in updates:
        schedule.comment = updates["comment"]

    await session.commit()
    await session.refresh(schedule)
    return {"schedule": _schedule_to_schema(schedule)}


@router.delete("/schedules/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    """Delete schedule row."""
    schedule = await _get_schedule_or_404(session, schedule_id)
    await _require_schedule_access(session, current_user, schedule.user_id)

    await session.delete(schedule)
    await session.commit()


@router.get("/projects/{project_id}/schedules", response_model=schemas.PagedSchedulesWithUser)
async def list_project_schedules(
    project_id: UUID,
    session: Session,
    current_user: CurrentUser,
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List schedules for all direct project participants (project admin only)."""
    _validate_period(date_from, date_to)
    await access_control.ensure_project_admin_context(
        session,
        project_id,
        current_user.id,
        current_user=current_user,
    )

    participant_ids_query = select(ProjectUser.user_id).where(ProjectUser.project_id == project_id)
    query = (
        select(Schedule, User)
        .join(User, User.id == Schedule.user_id)
        .where(Schedule.user_id.in_(participant_ids_query))
    )
    if date_from is not None:
        query = query.where(Schedule.date >= date_from)
    if date_to is not None:
        query = query.where(Schedule.date <= date_to)

    total = (await session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    rows = (
        await session.execute(
            query.order_by(Schedule.date.desc(), User.full_name.asc()).offset(offset).limit(limit)
        )
    ).all()

    items: list[schemas.ScheduleWithUser] = []
    for schedule, user in rows:
        base = _schedule_to_schema(schedule)
        items.append(
            schemas.ScheduleWithUser(
                **base.model_dump(),
                user=_user_lite_to_schema(user),
            )
        )

    return schemas.PagedSchedulesWithUser(items=items, total=total)
