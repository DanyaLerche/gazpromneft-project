from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import schemas
from backend.models import Project, ProjectUser, User

LEGACY_MEMBER_PROJECT_ROLE_VALUES = frozenset({"project_member"})
LEGACY_ADMIN_PROJECT_ROLE_VALUES = frozenset({"project_admin", "project_owner"})
DB_MEMBER_PROJECT_ROLE_VALUES = frozenset({schemas.ProjectRole.USER.value})
DB_ADMIN_PROJECT_ROLE_VALUES = frozenset({schemas.ProjectRole.ADMIN_PROJECT.value})
MEMBER_PROJECT_ROLE_VALUES = frozenset(
    {*DB_MEMBER_PROJECT_ROLE_VALUES, *LEGACY_MEMBER_PROJECT_ROLE_VALUES}
)
ADMIN_PROJECT_ROLE_VALUES = frozenset(
    {*DB_ADMIN_PROJECT_ROLE_VALUES, *LEGACY_ADMIN_PROJECT_ROLE_VALUES}
)
KNOWN_PROJECT_ROLE_VALUES = MEMBER_PROJECT_ROLE_VALUES | ADMIN_PROJECT_ROLE_VALUES


@dataclass(frozen=True, slots=True)
class ProjectAccessContext:
    project: Project
    user_id: UUID
    app_role: schemas.AppRole
    project_role: schemas.ProjectRole | None
    membership: ProjectUser | None

    @property
    def is_admin_app(self) -> bool:
        return self.app_role == schemas.AppRole.ADMIN_APP

    @property
    def is_member(self) -> bool:
        return self.project_role is not None

    @property
    def is_admin(self) -> bool:
        return self.project_role == schemas.ProjectRole.ADMIN_PROJECT


def _coerce_app_role(role: str | schemas.AppRole) -> schemas.AppRole:
    if isinstance(role, schemas.AppRole):
        return role
    try:
        return schemas.AppRole(role)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=f"Unsupported app role: {role}") from exc


def normalize_project_role(role: str | schemas.ProjectRole | None) -> schemas.ProjectRole | None:
    if role is None:
        return None
    if isinstance(role, schemas.ProjectRole):
        return role
    if role in ADMIN_PROJECT_ROLE_VALUES:
        return schemas.ProjectRole.ADMIN_PROJECT
    if role in MEMBER_PROJECT_ROLE_VALUES:
        return schemas.ProjectRole.USER
    raise HTTPException(status_code=500, detail=f"Unsupported project role: {role}")


def is_admin_app_user(user: User | None) -> bool:
    return user is not None and _coerce_app_role(user.app_role) == schemas.AppRole.ADMIN_APP


async def ensure_admin_app(
    session: AsyncSession,
    user_id: UUID,
    *,
    current_user: User | None = None,
) -> None:
    if await is_admin_app(session, user_id, current_user=current_user):
        return

    raise HTTPException(status_code=403, detail="admin_app role is required")


async def get_user_or_404(session: AsyncSession, user_id: UUID) -> User:
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def get_user_app_role(
    session: AsyncSession,
    user_id: UUID,
    *,
    current_user: User | None = None,
) -> schemas.AppRole:
    if current_user is not None:
        if current_user.id != user_id:
            raise HTTPException(status_code=500, detail="current_user does not match requested user")
        return _coerce_app_role(current_user.app_role)
    user = await get_user_or_404(session, user_id)
    return _coerce_app_role(user.app_role)


async def get_project_or_404(session: AsyncSession, project_id: UUID) -> Project:
    project = (await session.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def is_admin_app(
    session: AsyncSession,
    user_id: UUID,
    *,
    current_user: User | None = None,
) -> bool:
    return await get_user_app_role(session, user_id, current_user=current_user) == schemas.AppRole.ADMIN_APP


async def get_project_membership(
    session: AsyncSession,
    project_id: UUID,
    user_id: UUID,
) -> ProjectUser | None:
    return (
        await session.execute(
            select(ProjectUser).where(
                ProjectUser.project_id == project_id,
                ProjectUser.user_id == user_id,
            )
        )
    ).scalar_one_or_none()


async def get_project_access_context(
    session: AsyncSession,
    project_id: UUID,
    user_id: UUID,
    *,
    current_user: User | None = None,
) -> ProjectAccessContext:
    project = await get_project_or_404(session, project_id)
    app_role = await get_user_app_role(session, user_id, current_user=current_user)
    if app_role == schemas.AppRole.ADMIN_APP:
        return ProjectAccessContext(
            project=project,
            user_id=user_id,
            app_role=app_role,
            project_role=schemas.ProjectRole.ADMIN_PROJECT,
            membership=None,
        )

    membership = await get_project_membership(session, project_id, user_id)
    return ProjectAccessContext(
        project=project,
        user_id=user_id,
        app_role=app_role,
        project_role=normalize_project_role(membership.role) if membership is not None else None,
        membership=membership,
    )


async def resolve_project_role(
    session: AsyncSession,
    project_id: UUID,
    user_id: UUID,
    *,
    current_user: User | None = None,
) -> schemas.ProjectRole | None:
    access = await get_project_access_context(
        session,
        project_id,
        user_id,
        current_user=current_user,
    )
    return access.project_role


async def get_direct_project_ids(
    session: AsyncSession,
    user_id: UUID,
) -> set[UUID]:
    project_ids = (
        await session.execute(select(ProjectUser.project_id).where(ProjectUser.user_id == user_id))
    ).scalars().all()
    return set(project_ids)


async def ensure_project_member_context(
    session: AsyncSession,
    project_id: UUID,
    user_id: UUID,
    *,
    current_user: User | None = None,
) -> ProjectAccessContext:
    access = await get_project_access_context(
        session,
        project_id,
        user_id,
        current_user=current_user,
    )
    if not access.is_member:
        raise HTTPException(status_code=403, detail="No access to project")
    return access


async def ensure_project_admin_context(
    session: AsyncSession,
    project_id: UUID,
    user_id: UUID,
    *,
    current_user: User | None = None,
) -> ProjectAccessContext:
    access = await ensure_project_member_context(
        session,
        project_id,
        user_id,
        current_user=current_user,
    )
    if not access.is_admin:
        raise HTTPException(status_code=403, detail="Project admin role is required")
    return access


async def ensure_project_access(
    session: AsyncSession,
    project_id: UUID,
    user_id: UUID,
    *,
    current_user: User | None = None,
) -> Project:
    access = await ensure_project_member_context(
        session,
        project_id,
        user_id,
        current_user=current_user,
    )
    return access.project


async def ensure_project_admin(
    session: AsyncSession,
    project_id: UUID,
    user_id: UUID,
    *,
    current_user: User | None = None,
) -> Project:
    access = await ensure_project_admin_context(
        session,
        project_id,
        user_id,
        current_user=current_user,
    )
    return access.project


async def has_any_direct_admin_project_membership(
    session: AsyncSession,
    user_id: UUID,
) -> bool:
    admin_membership_count = (
        await session.execute(
            select(func.count())
            .select_from(ProjectUser)
            .where(
                ProjectUser.user_id == user_id,
                ProjectUser.role.in_(tuple(DB_ADMIN_PROJECT_ROLE_VALUES)),
            )
        )
    ).scalar_one()
    return admin_membership_count > 0


async def can_create_projects(
    session: AsyncSession,
    user_id: UUID,
    *,
    current_user: User | None = None,
) -> bool:
    # Any authenticated user can create projects.
    await get_user_app_role(session, user_id, current_user=current_user)
    return True


async def ensure_can_create_projects(
    session: AsyncSession,
    user_id: UUID,
    *,
    current_user: User | None = None,
) -> None:
    if not await can_create_projects(session, user_id, current_user=current_user):
        raise HTTPException(status_code=403, detail="Project creation is not allowed")


async def get_accessible_project_ids(
    session: AsyncSession,
    user_id: UUID,
    *,
    current_user: User | None = None,
) -> set[UUID]:
    if await is_admin_app(session, user_id, current_user=current_user):
        project_ids = (await session.execute(select(Project.id))).scalars().all()
        return set(project_ids)

    return await get_direct_project_ids(session, user_id)


async def get_admin_project_ids(
    session: AsyncSession,
    user_id: UUID,
    *,
    current_user: User | None = None,
) -> set[UUID]:
    if await is_admin_app(session, user_id, current_user=current_user):
        project_ids = (await session.execute(select(Project.id))).scalars().all()
        return set(project_ids)

    project_ids = (
        await session.execute(
            select(ProjectUser.project_id).where(
                ProjectUser.user_id == user_id,
                ProjectUser.role.in_(tuple(DB_ADMIN_PROJECT_ROLE_VALUES)),
            )
        )
    ).scalars().all()
    return set(project_ids)


async def get_effective_project_roles(
    session: AsyncSession,
    user_id: UUID,
    project_ids: Iterable[UUID],
    *,
    current_user: User | None = None,
) -> dict[UUID, schemas.ProjectRole]:
    project_ids = set(project_ids)
    if not project_ids:
        return {}

    if await is_admin_app(session, user_id, current_user=current_user):
        return {project_id: schemas.ProjectRole.ADMIN_PROJECT for project_id in project_ids}

    rows = (
        await session.execute(
            select(ProjectUser.project_id, ProjectUser.role).where(
                ProjectUser.user_id == user_id,
                ProjectUser.project_id.in_(project_ids),
            )
        )
    ).all()

    roles: dict[UUID, schemas.ProjectRole] = {}
    for project_id, role in rows:
        normalized_role = normalize_project_role(role)
        if normalized_role is not None:
            roles[project_id] = normalized_role
    return roles


async def user_has_direct_membership_in_projects(
    session: AsyncSession,
    user_id: UUID,
    project_ids: Iterable[UUID],
) -> bool:
    project_ids = set(project_ids)
    if not project_ids:
        return False

    membership_count = (
        await session.execute(
            select(func.count())
            .select_from(ProjectUser)
            .where(
                ProjectUser.user_id == user_id,
                ProjectUser.project_id.in_(project_ids),
            )
        )
    ).scalar_one()
    return membership_count > 0


async def can_manage_user_in_admin_scope(
    session: AsyncSession,
    actor_id: UUID,
    target_user_id: UUID,
    *,
    current_user: User | None = None,
) -> bool:
    if actor_id == target_user_id:
        return True

    if await is_admin_app(session, actor_id, current_user=current_user):
        return True

    admin_project_ids = await get_admin_project_ids(
        session,
        actor_id,
        current_user=current_user,
    )
    return await user_has_direct_membership_in_projects(
        session,
        target_user_id,
        admin_project_ids,
    )


async def ensure_can_manage_user_in_admin_scope(
    session: AsyncSession,
    actor_id: UUID,
    target_user_id: UUID,
    *,
    current_user: User | None = None,
) -> None:
    if await can_manage_user_in_admin_scope(
        session,
        actor_id,
        target_user_id,
        current_user=current_user,
    ):
        return

    raise HTTPException(status_code=403, detail="No access to the requested user scope")


async def count_direct_admin_project_members(session: AsyncSession, project_id: UUID) -> int:
    return (
        await session.execute(
            select(func.count())
            .select_from(ProjectUser)
            .where(
                ProjectUser.project_id == project_id,
                ProjectUser.role.in_(tuple(DB_ADMIN_PROJECT_ROLE_VALUES)),
            )
        )
    ).scalar_one()


async def ensure_not_last_direct_admin(
    session: AsyncSession,
    project_id: UUID,
    target_user_id: UUID,
    *,
    next_role: schemas.ProjectRole | None,
) -> None:
    membership = await get_project_membership(session, project_id, target_user_id)
    if membership is None or normalize_project_role(membership.role) != schemas.ProjectRole.ADMIN_PROJECT:
        return
    if next_role == schemas.ProjectRole.ADMIN_PROJECT:
        return

    admin_count = await count_direct_admin_project_members(session, project_id)
    if admin_count <= 1:
        raise HTTPException(
            status_code=409,
            detail="Project must have at least one direct admin_project member",
        )


async def count_active_admin_app_users(session: AsyncSession) -> int:
    return (
        await session.execute(
            select(func.count())
            .select_from(User)
            .where(
                User.app_role == schemas.AppRole.ADMIN_APP.value,
                User.is_active.is_(True),
            )
        )
    ).scalar_one()


async def ensure_not_last_admin_app(
    session: AsyncSession,
    target_user_id: UUID,
    *,
    next_app_role: schemas.AppRole,
) -> User:
    user = await get_user_or_404(session, target_user_id)
    if _coerce_app_role(user.app_role) != schemas.AppRole.ADMIN_APP:
        return user
    if next_app_role == schemas.AppRole.ADMIN_APP:
        return user
    if not user.is_active:
        return user

    admin_count = await count_active_admin_app_users(session)
    if admin_count <= 1:
        raise HTTPException(
            status_code=409,
            detail="Platform must have at least one active admin_app user",
        )
    return user
