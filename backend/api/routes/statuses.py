from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from backend import schemas
from backend.api.dependencies import CurrentUser, Session
from backend.api.status_defaults import ensure_project_statuses
from backend.models import Issue, Status
from backend.services import access_control

router = APIRouter(tags=["Statuses"])


def _status_to_schema(status: Status) -> schemas.Status:
    return schemas.Status(
        id=status.id,
        project_id=status.project_id,
        name=status.name,
        category=schemas.StatusCategory(status.category),
        sort_order=status.sort_order,
    )


@router.get("/projects/{project_id}/statuses", response_model=schemas.StatusListResponse)
async def list_statuses(
    project_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    """РџРѕР»СѓС‡РёС‚СЊ СЃС‚Р°С‚СѓСЃС‹ РїСЂРѕРµРєС‚Р°."""
    await access_control.ensure_project_access(
        session,
        project_id,
        current_user.id,
        current_user=current_user,
    )
    statuses = await ensure_project_statuses(session, project_id, auto_commit=True)
    return {"items": [_status_to_schema(status) for status in statuses]}


@router.post("/projects/{project_id}/statuses", status_code=201, response_model=schemas.StatusResponse)
async def create_status(
    project_id: UUID,
    body: schemas.CreateStatusRequest,
    session: Session,
    current_user: CurrentUser,
):
    """РЎРѕР·РґР°С‚СЊ СЃС‚Р°С‚СѓСЃ. РўСЂРµР±СѓРµС‚ admin_project."""
    await access_control.ensure_project_admin(
        session,
        project_id,
        current_user.id,
        current_user=current_user,
    )
    status = Status(
        project_id=project_id,
        name=body.name,
        category=body.category.value,
        sort_order=body.sort_order,
    )
    session.add(status)
    try:
        await session.commit()
        await session.refresh(status)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="РЎС‚Р°С‚СѓСЃ СЃ С‚Р°РєРёРј РёРјРµРЅРµРј СѓР¶Рµ РµСЃС‚СЊ РІ РїСЂРѕРµРєС‚Рµ")
    return {"status": _status_to_schema(status)}


@router.patch("/statuses/{status_id}", response_model=schemas.StatusResponse)
async def update_status(
    status_id: UUID,
    body: schemas.UpdateStatusRequest,
    session: Session,
    current_user: CurrentUser,
):
    """РћР±РЅРѕРІРёС‚СЊ СЃС‚Р°С‚СѓСЃ. РўСЂРµР±СѓРµС‚ admin_project."""
    status = (await session.execute(select(Status).where(Status.id == status_id))).scalar_one_or_none()
    if not status:
        raise HTTPException(status_code=404, detail="РЎС‚Р°С‚СѓСЃ РЅРµ РЅР°Р№РґРµРЅ")

    await access_control.ensure_project_admin(
        session,
        status.project_id,
        current_user.id,
        current_user=current_user,
    )
    if body.name is not None:
        status.name = body.name
    if body.category is not None:
        status.category = body.category.value
    if body.sort_order is not None:
        status.sort_order = body.sort_order

    try:
        await session.commit()
        await session.refresh(status)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="РЎС‚Р°С‚СѓСЃ СЃ С‚Р°РєРёРј РёРјРµРЅРµРј СѓР¶Рµ РµСЃС‚СЊ")
    return {"status": _status_to_schema(status)}


@router.delete("/statuses/{status_id}", status_code=204)
async def delete_status(
    status_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    """РЈРґР°Р»РёС‚СЊ СЃС‚Р°С‚СѓСЃ. РўСЂРµР±СѓРµС‚ admin_project."""
    status = (await session.execute(select(Status).where(Status.id == status_id))).scalar_one_or_none()
    if not status:
        raise HTTPException(status_code=404, detail="РЎС‚Р°С‚СѓСЃ РЅРµ РЅР°Р№РґРµРЅ")

    await access_control.ensure_project_admin(
        session,
        status.project_id,
        current_user.id,
        current_user=current_user,
    )
    issues_count = (
        await session.execute(
            select(func.count()).select_from(Issue).where(Issue.status_id == status_id)
        )
    ).scalar_one()
    if issues_count > 0:
        raise HTTPException(status_code=409, detail="РќРµР»СЊР·СЏ СѓРґР°Р»РёС‚СЊ СЃС‚Р°С‚СѓСЃ: РµСЃС‚СЊ Р·Р°РґР°С‡Рё РІ СЌС‚РѕРј СЃС‚Р°С‚СѓСЃРµ")

    await session.delete(status)
    await session.commit()
