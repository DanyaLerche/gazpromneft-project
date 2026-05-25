# Эндпоинты проектов, настроек и участников.
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from backend import schemas
from backend.api.dependencies import CurrentUser, Session
from backend.api.status_defaults import ensure_project_statuses
from backend.models import Issue, Project, ProjectUser, User, UserProjectPreference
from backend.services import access_control
from backend.services import onboarding as onboarding_service

router = APIRouter(prefix="/projects", tags=["Projects"])


def _user_to_schema(user: User) -> schemas.User:
    return schemas.User.model_validate(user)


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


def _map_onboarding_reads(
    items: list[onboarding_service.OnboardingListItem],
) -> list[schemas.OnboardingReadItem]:
    return [
        schemas.OnboardingReadItem(
            page_id=item.id,
            title=item.title,
            reason=item.reason,
            score=item.score,
        )
        for item in items
    ]


def _map_onboarding_issues(
    items: list[onboarding_service.OnboardingListItem],
) -> list[schemas.OnboardingIssueToReviewItem]:
    return [
        schemas.OnboardingIssueToReviewItem(
            issue_id=item.id,
            title=item.title,
            reason=item.reason,
            score=item.score,
        )
        for item in items
    ]


def _map_onboarding_people(
    items: list[onboarding_service.OnboardingPersonItem],
) -> list[schemas.OnboardingKeyPersonItem]:
    return [
        schemas.OnboardingKeyPersonItem(
            user_id=item.id,
            full_name=item.full_name,
            email=item.email,
            reason=item.reason,
            score=item.score,
        )
        for item in items
    ]


def _map_onboarding_assignees(
    rows: list[tuple[User, bool]],
) -> list[schemas.OnboardingAssigneeItem]:
    assignees: list[schemas.OnboardingAssigneeItem] = []
    for user, is_assigned in rows:
        if not is_assigned:
            continue
        assignees.append(
            schemas.OnboardingAssigneeItem(
                user_id=user.id,
                full_name=user.full_name,
                email=user.email,
            )
        )
    return assignees


async def _get_project_preferences(
    session: Session,
    project_id: UUID,
    user_id: UUID,
) -> schemas.ProjectOnboardingPreferences:
    preferences = (
        await session.execute(
            select(UserProjectPreference).where(
                UserProjectPreference.project_id == project_id,
                UserProjectPreference.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    return schemas.ProjectOnboardingPreferences(
        new_employee_mode=preferences.new_employee_mode if preferences is not None else False
    )


async def _get_project_onboarding_assignees(
    session: Session,
    project_id: UUID,
) -> list[schemas.OnboardingAssigneeItem]:
    preferences_sq = (
        select(
            UserProjectPreference.user_id.label("user_id"),
            UserProjectPreference.new_employee_mode.label("new_employee_mode"),
        )
        .where(UserProjectPreference.project_id == project_id)
        .subquery()
    )
    rows = (
        await session.execute(
            select(
                User,
                func.coalesce(preferences_sq.c.new_employee_mode, False).label("is_assigned"),
            )
            .select_from(ProjectUser)
            .join(User, User.id == ProjectUser.user_id)
            .outerjoin(preferences_sq, preferences_sq.c.user_id == User.id)
            .where(ProjectUser.project_id == project_id)
            .order_by(User.full_name.asc(), User.email.asc())
        )
    ).all()
    return _map_onboarding_assignees(rows)


@router.get("", response_model=schemas.PagedProjects)
async def list_projects(
    session: Session,
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Список проектов текущего пользователя."""
    if access_control.is_admin_app_user(current_user):
        total = (await session.execute(select(func.count()).select_from(Project))).scalar_one()
        projects = (
            await session.execute(
                select(Project).order_by(Project.created_at.desc()).offset(offset).limit(limit)
            )
        ).scalars().all()

        return schemas.PagedProjects(
            items=[_project_to_schema(project, schemas.ProjectRole.ADMIN_PROJECT) for project in projects],
            total=total,
        )

    total = (
        await session.execute(
            select(func.count())
            .select_from(ProjectUser)
            .where(ProjectUser.user_id == current_user.id)
        )
    ).scalar_one()
    project_users = (
        await session.execute(
            select(ProjectUser)
            .where(ProjectUser.user_id == current_user.id)
            .options(selectinload(ProjectUser.project))
            .order_by(ProjectUser.project_id)
            .offset(offset)
            .limit(limit)
        )
    ).scalars().unique().all()

    items = [
        _project_to_schema(
            project_user.project,
            access_control.normalize_project_role(project_user.role),
        )
        for project_user in project_users
    ]
    items.sort(key=lambda project: project.created_at, reverse=True)
    return schemas.PagedProjects(items=items, total=total)


@router.post("", status_code=201, response_model=schemas.ProjectResponseWrapper)
async def create_project(
    body: schemas.CreateProjectRequest,
    session: Session,
    current_user: CurrentUser,
):
    """Создать проект."""
    await access_control.ensure_can_create_projects(
        session,
        current_user.id,
        current_user=current_user,
    )

    project = Project(
        key=body.key.upper(),
        name=body.name.strip(),
        description="",
        category=schemas.ProjectCategory.SOFTWARE.value,
        created_by=current_user.id,
    )
    session.add(project)
    creator_is_admin_app = access_control.is_admin_app_user(current_user)
    try:
        await session.flush()
        if not creator_is_admin_app:
            session.add(
                ProjectUser(
                    project_id=project.id,
                    user_id=current_user.id,
                    role=schemas.ProjectRole.ADMIN_PROJECT.value,
                )
            )
        await ensure_project_statuses(session, project.id)
        await session.commit()
        await session.refresh(project)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Data conflict (project key is already used)")

    return {"project": _project_to_schema(project, schemas.ProjectRole.ADMIN_PROJECT)}


@router.get("/{project_id}", response_model=schemas.ProjectResponseWrapper)
async def get_project(
    project_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    """Получить проект."""
    access = await access_control.ensure_project_member_context(
        session,
        project_id,
        current_user.id,
        current_user=current_user,
    )
    return {"project": _project_to_schema(access.project, access.project_role)}


@router.get(
    "/{project_id}/onboarding/recommendations",
    response_model=schemas.OnboardingRecommendationsResponse,
)
async def get_onboarding_recommendations(
    project_id: UUID,
    session: Session,
    current_user: CurrentUser,
    force: bool = Query(False, description="Игнорировать кэш и пересчитать рекомендации"),
):
    result = await onboarding_service.get_or_compute_onboarding_recommendations(
        session,
        project_id,
        current_user,
        force=force,
    )
    return schemas.OnboardingRecommendationsResponse(
        reads=_map_onboarding_reads(result.recommendations.reads),
        issues_to_review=_map_onboarding_issues(result.recommendations.issues_to_review),
        key_people=_map_onboarding_people(result.recommendations.key_people),
        generated_at=result.generated_at,
        cached=result.cached,
    )


@router.get(
    "/{project_id}/me/preferences",
    response_model=schemas.ProjectOnboardingPreferencesResponse,
)
async def get_my_project_preferences(
    project_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    await access_control.ensure_project_member_context(
        session,
        project_id,
        current_user.id,
        current_user=current_user,
    )
    return schemas.ProjectOnboardingPreferencesResponse(
        preferences=await _get_project_preferences(session, project_id, current_user.id)
    )


@router.get(
    "/{project_id}/onboarding/assignees",
    response_model=schemas.ProjectOnboardingAssigneesResponse,
)
async def get_project_onboarding_assignees(
    project_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    await access_control.ensure_project_member_context(
        session,
        project_id,
        current_user.id,
        current_user=current_user,
    )
    return schemas.ProjectOnboardingAssigneesResponse(
        assignees=await _get_project_onboarding_assignees(session, project_id)
    )


@router.patch(
    "/{project_id}/onboarding/assignees",
    response_model=schemas.ProjectOnboardingAssigneesResponse,
)
async def update_project_onboarding_assignees(
    project_id: UUID,
    body: schemas.UpdateProjectOnboardingAssigneesRequest,
    session: Session,
    current_user: CurrentUser,
):
    await access_control.ensure_project_admin_context(
        session,
        project_id,
        current_user.id,
        current_user=current_user,
    )

    member_ids = set(
        (
            await session.execute(
                select(ProjectUser.user_id).where(ProjectUser.project_id == project_id)
            )
        )
        .scalars()
        .all()
    )
    requested_ids = list(dict.fromkeys(body.user_ids))
    unknown_ids = [str(user_id) for user_id in requested_ids if user_id not in member_ids]
    if unknown_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown or non-member users in assignees: {', '.join(unknown_ids)}",
        )

    for user_id in requested_ids:
        await session.execute(
            insert(UserProjectPreference)
            .values(
                project_id=project_id,
                user_id=user_id,
                new_employee_mode=True,
            )
            .on_conflict_do_update(
                index_elements=["project_id", "user_id"],
                set_={"new_employee_mode": True, "updated_at": func.now()},
            )
        )

    if member_ids:
        stmt = (
            update(UserProjectPreference)
            .where(
                UserProjectPreference.project_id == project_id,
                UserProjectPreference.user_id.in_(member_ids),
            )
            .values(new_employee_mode=False)
        )
        if requested_ids:
            stmt = stmt.where(UserProjectPreference.user_id.not_in(requested_ids))
        await session.execute(stmt)

    await session.commit()
    return schemas.ProjectOnboardingAssigneesResponse(
        assignees=await _get_project_onboarding_assignees(session, project_id)
    )


@router.patch(
    "/{project_id}/me/preferences",
    response_model=schemas.ProjectOnboardingPreferencesResponse,
)
async def update_my_project_preferences(
    project_id: UUID,
    body: schemas.UpdateProjectOnboardingPreferencesRequest,
    session: Session,
    current_user: CurrentUser,
):
    await access_control.ensure_project_member_context(
        session,
        project_id,
        current_user.id,
        current_user=current_user,
    )

    preference = (
        await session.execute(
            select(UserProjectPreference).where(
                UserProjectPreference.project_id == project_id,
                UserProjectPreference.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()
    if preference is None:
        preference = UserProjectPreference(
            project_id=project_id,
            user_id=current_user.id,
            new_employee_mode=body.new_employee_mode,
        )
        session.add(preference)
    else:
        preference.new_employee_mode = body.new_employee_mode

    await session.commit()
    return schemas.ProjectOnboardingPreferencesResponse(
        preferences=schemas.ProjectOnboardingPreferences(
            new_employee_mode=preference.new_employee_mode
        )
    )


@router.patch("/{project_id}", response_model=schemas.ProjectResponseWrapper)
async def update_project(
    project_id: UUID,
    body: schemas.UpdateProjectRequest,
    session: Session,
    current_user: CurrentUser,
):
    """Обновить настройки проекта. Требует admin_project."""
    access = await access_control.ensure_project_admin_context(
        session,
        project_id,
        current_user.id,
        current_user=current_user,
    )
    project = access.project

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="At least one project setting must be provided")

    if "name" in updates and updates["name"] is not None:
        project.name = updates["name"].strip()
    if "description" in updates and updates["description"] is not None:
        project.description = updates["description"].strip()
    if "category" in updates and updates["category"] is not None:
        project.category = updates["category"].value

    await session.commit()
    await session.refresh(project)
    return {"project": _project_to_schema(project, access.project_role)}


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    """Удалить проект. Разрешено только для пустого проекта."""
    access = await access_control.ensure_project_admin_context(
        session,
        project_id,
        current_user.id,
        current_user=current_user,
    )

    issues_count = (
        await session.execute(
            select(func.count()).select_from(Issue).where(Issue.project_id == project_id)
        )
    ).scalar_one()
    if issues_count > 0:
        raise HTTPException(
            status_code=409,
            detail="Проект нельзя удалить, пока в нем есть задачи. Сначала удалите связанные задачи.",
        )

    await session.execute(delete(ProjectUser).where(ProjectUser.project_id == project_id))
    await session.execute(delete(Project).where(Project.id == project_id))
    await session.commit()


@router.get("/{project_id}/users", response_model=schemas.PagedProjectUsers)
async def list_project_users(
    project_id: UUID,
    session: Session,
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Список участников проекта."""
    await access_control.ensure_project_member_context(
        session,
        project_id,
        current_user.id,
        current_user=current_user,
    )
    total = (
        await session.execute(
            select(func.count()).select_from(ProjectUser).where(ProjectUser.project_id == project_id)
        )
    ).scalar_one()
    project_users = (
        await session.execute(
            select(ProjectUser)
            .where(ProjectUser.project_id == project_id)
            .options(selectinload(ProjectUser.user))
            .order_by(ProjectUser.user_id)
            .offset(offset)
            .limit(limit)
        )
    ).scalars().unique().all()
    items = [
        schemas.ProjectUserExpanded(
            user=_user_to_schema(project_user.user),
            role=access_control.normalize_project_role(project_user.role),
        )
        for project_user in project_users
    ]
    return schemas.PagedProjectUsers(items=items, total=total)


@router.get("/{project_id}/users/search", response_model=schemas.PagedUsers)
async def search_project_users(
    project_id: UUID,
    session: Session,
    current_user: CurrentUser,
    q: str | None = Query(None, max_length=200),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Поиск пользователей, которых можно добавить в проект. Требует admin_project."""
    await access_control.ensure_project_admin_context(
        session,
        project_id,
        current_user.id,
        current_user=current_user,
    )

    existing_user_ids = select(ProjectUser.user_id).where(ProjectUser.project_id == project_id)
    query = select(User).where(
        User.is_active.is_(True),
        User.app_role == schemas.AppRole.USER.value,
        User.id.not_in(existing_user_ids),
    )
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(
            or_(
                User.email.ilike(pattern),
                User.full_name.ilike(pattern),
            )
        )

    total = (await session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    users = (
        await session.execute(query.order_by(User.full_name.asc()).offset(offset).limit(limit))
    ).scalars().all()
    return schemas.PagedUsers(items=[_user_to_schema(user) for user in users], total=total)


@router.post("/{project_id}/users", status_code=201, response_model=schemas.ProjectUser)
async def add_project_user(
    project_id: UUID,
    body: schemas.AddProjectUserRequest,
    session: Session,
    current_user: CurrentUser,
):
    """Добавить пользователя в проект. Требует admin_project."""
    await access_control.ensure_project_admin_context(
        session,
        project_id,
        current_user.id,
        current_user=current_user,
    )
    user = (await session.execute(select(User).where(User.id == body.user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive users cannot be added to project")
    if user.app_role == schemas.AppRole.ADMIN_APP.value:
        raise HTTPException(
            status_code=400,
            detail="admin_app users have virtual access and are not added to project members",
        )

    session.add(
        ProjectUser(
            project_id=project_id,
            user_id=body.user_id,
            role=body.role.value,
        )
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="User is already in the project")

    return schemas.ProjectUser(
        project_id=project_id,
        user_id=body.user_id,
        role=body.role,
    )


@router.patch("/{project_id}/users/{user_id}", response_model=schemas.ProjectUser)
async def update_project_user(
    project_id: UUID,
    user_id: UUID,
    body: schemas.UpdateProjectUserRequest,
    session: Session,
    current_user: CurrentUser,
):
    """Изменить роль участника проекта. Требует admin_project."""
    await access_control.ensure_project_admin_context(
        session,
        project_id,
        current_user.id,
        current_user=current_user,
    )
    project_user = await access_control.get_project_membership(session, project_id, user_id)
    if project_user is None:
        raise HTTPException(status_code=404, detail="Project member not found")

    await access_control.ensure_not_last_direct_admin(
        session,
        project_id,
        user_id,
        next_role=body.role,
    )
    project_user.role = body.role.value
    await session.commit()
    return schemas.ProjectUser(project_id=project_id, user_id=user_id, role=body.role)


@router.delete("/{project_id}/users/{user_id}", status_code=204)
async def remove_project_user(
    project_id: UUID,
    user_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    """Удалить пользователя из проекта. Требует admin_project."""
    await access_control.ensure_project_admin_context(
        session,
        project_id,
        current_user.id,
        current_user=current_user,
    )
    project_user = await access_control.get_project_membership(session, project_id, user_id)
    if project_user is None:
        raise HTTPException(status_code=404, detail="Project member not found")

    await access_control.ensure_not_last_direct_admin(
        session,
        project_id,
        user_id,
        next_role=None,
    )
    await session.delete(project_user)
    await session.commit()
