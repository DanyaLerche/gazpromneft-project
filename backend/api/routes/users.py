from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import func, or_, select

from backend import schemas
from backend.api.dependencies import CurrentUser, Session
from backend.models import User
from backend.services import access_control

router = APIRouter(prefix="/users", tags=["Users"])


def _user_to_schema(user: User) -> schemas.User:
    return schemas.User.model_validate(user)


@router.get("", response_model=schemas.PagedUsers)
async def list_users(
    session: Session,
    current_user: CurrentUser,
    q: str | None = Query(None, max_length=200),
    app_role: schemas.AppRole | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    await access_control.ensure_admin_app(
        session,
        current_user.id,
        current_user=current_user,
    )

    query = select(User)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(
            or_(
                User.email.ilike(pattern),
                User.full_name.ilike(pattern),
            )
        )
    if app_role is not None:
        query = query.where(User.app_role == app_role.value)

    total = (await session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    users = (
        await session.execute(
            query.order_by(User.full_name.asc(), User.email.asc()).offset(offset).limit(limit)
        )
    ).scalars().all()
    return schemas.PagedUsers(items=[_user_to_schema(user) for user in users], total=total)


@router.patch("/{user_id}", response_model=schemas.User)
async def update_user_app_role(
    user_id: UUID,
    body: schemas.UpdateUserAppRoleRequest,
    session: Session,
    current_user: CurrentUser,
):
    await access_control.ensure_admin_app(
        session,
        current_user.id,
        current_user=current_user,
    )

    user = await access_control.ensure_not_last_admin_app(
        session,
        user_id,
        next_app_role=body.app_role,
    )
    if schemas.AppRole(user.app_role) != body.app_role:
        user.app_role = body.app_role.value
        await session.commit()
        await session.refresh(user)

    return _user_to_schema(user)
