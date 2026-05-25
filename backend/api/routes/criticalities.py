# Эндпоинты критичности по OpenAPI (openapi-v0.1.0.yaml).
from fastapi import APIRouter, Depends

from sqlalchemy import select

from backend import schemas
from backend.api.dependencies import CurrentUser, Session
from backend.models import Criticality


router = APIRouter(prefix="/criticalities", tags=["Criticalities"])


def _criticality_to_schema(c: Criticality) -> schemas.Criticality:
    return schemas.Criticality(id=c.id, name=c.name, level=c.level)


@router.get("", response_model=schemas.CriticalityListResponse)
async def list_criticalities(
    session: Session,
    current_user: CurrentUser,
):
    """Справочник критичности (Low/Medium/High и т.п.)."""
    result = await session.execute(
        select(Criticality).order_by(Criticality.level)
    )
    items = [_criticality_to_schema(c) for c in result.scalars().all()]
    return {"items": items}
