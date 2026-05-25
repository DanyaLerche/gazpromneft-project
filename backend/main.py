from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.exc import ProgrammingError

from backend import schemas
from backend.auth.security import hash_password
from backend.database import async_session_maker, engine
from backend.models import (
    AuthCredential,
    AuthEvent,
    Criticality,
    EmailVerification,
    PendingRegistration,
    RefreshToken,
    User,
)
from backend.api.routes import auth as auth_router
from backend.api.routes import for_me as for_me_router
from backend.api.routes import projects as projects_router
from backend.api.routes import users as users_router
from backend.api.routes import statuses as statuses_router
from backend.api.routes import issues as issues_router
from backend.api.routes import attachments as attachments_router
from backend.api.routes import criticalities as criticalities_router
from backend.api.routes import schedules as schedules_router
from backend.api.routes import worklogs as worklogs_router
from backend.api.routes import wiki as wiki_router
from backend.api.routes import reports as reports_router
from backend.api.errors import register_error_handlers
from config import settings


logger = logging.getLogger(__name__)

OPENAPI_DESCRIPTION = """Контракты Backend/Frontend для таск-трекера.

Базовый префикс всех API-эндпоинтов: /api/v1
"""


async def _ensure_seed_user(
    session,
    *,
    email: str,
    full_name: str,
    password: str,
    app_role: schemas.AppRole = schemas.AppRole.USER,
    is_email_verified: bool = True,
) -> User:
    role_value = app_role.value
    user = (
        await session.execute(select(User).where(User.email == email).limit(1))
    ).scalar_one_or_none()
    if user is None:
        user = User(
            email=email,
            full_name=full_name,
            is_active=True,
            app_role=role_value,
            is_email_verified=is_email_verified,
        )
        session.add(user)
        await session.flush()
    elif user.app_role != role_value:
        user.app_role = role_value
    if user.is_email_verified != is_email_verified:
        user.is_email_verified = is_email_verified

    creds = (
        await session.execute(
            select(AuthCredential).where(AuthCredential.user_id == user.id).limit(1)
        )
    ).scalar_one_or_none()
    if creds is None:
        session.add(
            AuthCredential(
                user_id=user.id,
                password_hash=hash_password(password),
            )
        )

    return user


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS tracker"))
            await conn.run_sync(AuthCredential.__table__.create, checkfirst=True)
            await conn.run_sync(RefreshToken.__table__.create, checkfirst=True)
            await conn.run_sync(AuthEvent.__table__.create, checkfirst=True)
            await conn.run_sync(EmailVerification.__table__.create, checkfirst=True)
            await conn.run_sync(PendingRegistration.__table__.create, checkfirst=True)
    except ProgrammingError as exc:
        logger.warning(
            "Skipping auth table ensure during startup; database schema is not ready yet: %s",
            exc,
        )

    # Таблицы и схема tracker создаются миграциями Alembic.
    # Если миграции ещё не применены (relation "tracker.users" does not exist),
    # не падаем при старте приложения — просто пропускаем seed.
    async with async_session_maker() as session:
        try:
            await _ensure_seed_user(
                session,
                email="demo.user@example.com",
                full_name="Demo User",
                password=settings.AUTH_DEMO_PASSWORD,
                app_role=schemas.AppRole.ADMIN_APP,
            )
            await _ensure_seed_user(
                session,
                email="dev.one@example.com",
                full_name="Разработчик Один",
                password=settings.AUTH_DEV_ONE_PASSWORD,
                app_role=schemas.AppRole.USER,
            )

            first_crit = (
                await session.execute(select(Criticality).limit(1))
            ).scalar_one_or_none()
            if first_crit is None:
                for name, level in [("Low", 1), ("Medium", 2), ("High", 3)]:
                    session.add(Criticality(name=name, level=level))
            await session.commit()
        except ProgrammingError as exc:
            logger.warning(
                "Skipping DB seed during startup; database schema is not ready yet: %s",
                exc,
            )
    yield
    await engine.dispose()

app = FastAPI(
    title="Task Tracker API",
    version="0.1.0",
    description=OPENAPI_DESCRIPTION,
    lifespan=lifespan,
)

# Эндпоинты по OpenAPI (префикс /api/v1)
app.include_router(auth_router.router, prefix="/api/v1")
app.include_router(for_me_router.router, prefix="/api/v1")
app.include_router(projects_router.router, prefix="/api/v1")
app.include_router(users_router.router, prefix="/api/v1")
app.include_router(statuses_router.router, prefix="/api/v1")
app.include_router(issues_router.router, prefix="/api/v1")
app.include_router(attachments_router.router, prefix="/api/v1")
app.include_router(criticalities_router.router, prefix="/api/v1")
app.include_router(schedules_router.router, prefix="/api/v1")
app.include_router(worklogs_router.router, prefix="/api/v1")
app.include_router(wiki_router.router, prefix="/api/v1")
app.include_router(reports_router.router, prefix="/api/v1")
register_error_handlers(app)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # поменять на http://localhost:4200
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/auth.json", response_model=schemas.UserOut)
def get_auth():
    return USER_DEMO


@app.get("/api/project.json", response_model=schemas.ProjectOut)
def get_project():
    return PROJECT_DEMO


@app.get("/health")
def health():
    return {"status": "ok"}


# захардкодил словари для демонстрации

USER_DEMO = {
    "id": "u-42",
    "name": "Demo User",
    "email": "demo.user@example.com",
    "avatarUrl": "https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y",
}

ISSUES_DEMO = [
    {
        "id": "i-1",
        "title": "Backlog issue",
        "type": "Task",
        "status": "Backlog",
        "priority": "Medium",
        "listPosition": 1,
        "description": "<p>Это задача в Backlog.</p>",
        "createdAt": "2025-01-01T09:00:00.000Z",
        "updatedAt": "2025-01-01T09:10:00.000Z",
        "reporterId": "u-42",
        "userIds": ["u-42"],
        "comments": [],
        "projectId": "p-demo",
    },
    {
        "id": "i-2",
        "title": "Selected issue",
        "type": "Story",
        "status": "Selected",
        "priority": "High",
        "listPosition": 1,
        "description": "<p>Это задача в Selected.</p>",
        "createdAt": "2025-01-02T09:00:00.000Z",
        "updatedAt": "2025-01-02T09:20:00.000Z",
        "reporterId": "u-42",
        "userIds": ["u-42"],
        "comments": [],
        "projectId": "p-demo",
    },
    {
        "id": "i-3",
        "title": "In progress issue",
        "type": "Story",
        "status": "InProgress",
        "priority": "High",
        "listPosition": 1,
        "description": "<p>Это задача в In Progress.</p>",
        "createdAt": "2025-01-03T09:00:00.000Z",
        "updatedAt": "2025-01-03T09:30:00.000Z",
        "reporterId": "u-42",
        "userIds": ["u-42"],
        "comments": [],
        "projectId": "p-demo",
    },
    {
        "id": "i-4",
        "title": "Done issue",
        "type": "Bug",
        "status": "Done",
        "priority": "Low",
        "listPosition": 1,
        "description": "<p>Это задача в Done.</p>",
        "createdAt": "2025-01-04T09:00:00.000Z",
        "updatedAt": "2025-01-04T09:05:00.000Z",
        "reporterId": "u-42",
        "userIds": ["u-42"],
        "comments": [],
        "projectId": "p-demo",
    },
]

PROJECT_DEMO = {
    "id": "p-demo",
    "name": "Gaz Demo Project",
    "url": "http://localhost:4200",
    "description": "Project data is returned by FastAPI (hardcoded now, DB later).",
    "category": "Software",
    "createdAt": "2025-01-01T08:00:00.000Z",
    "updateAt": "2025-01-04T12:00:00.000Z",
    "issues": ISSUES_DEMO,
    "users": [
        {
            "id": "u-42",
            "name": "Demo User",
            "email": "demo.user@example.com",
            "avatarUrl": "https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y",
        }
    ],
}
