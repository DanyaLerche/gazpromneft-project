#Дефолтные статусы проекта для канбан-доски.
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Status


DEFAULT_PROJECT_STATUSES = (
    {"name": "К выполнению", "category": "todo", "sort_order": 10},
    {"name": "В работе", "category": "in_progress", "sort_order": 20},
    {"name": "Готово", "category": "done", "sort_order": 30},
)


async def load_project_statuses(session: AsyncSession, project_id: UUID) -> list[Status]:
    result = await session.execute(
        select(Status)
        .where(Status.project_id == project_id)
        .order_by(Status.sort_order, Status.name)
    )
    return list(result.scalars().all())


async def ensure_project_statuses(
    session: AsyncSession,
    project_id: UUID,
    *,
    auto_commit: bool = False,
) -> list[Status]:
    statuses = await load_project_statuses(session, project_id)
    if statuses:
        return statuses

    session.add_all(
        [Status(project_id=project_id, **payload) for payload in DEFAULT_PROJECT_STATUSES]
    )

    if auto_commit:
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()

    else:
        await session.flush()

    return await load_project_statuses(session, project_id)