# Схемы критичности из OpenAPI (openapi-v0.1.0.yaml).
from __future__ import annotations

from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Criticality(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    name: str
    level: int


class CriticalityListResponse(BaseModel):
    items: List[Criticality]
