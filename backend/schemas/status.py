# Схемы статусов из OpenAPI (openapi-v0.1.0.yaml).
from __future__ import annotations

from enum import Enum
from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class StatusCategory(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class Status(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    project_id: UUID
    name: str
    category: StatusCategory
    sort_order: int


class StatusListResponse(BaseModel):
    items: List[Status]


class StatusResponse(BaseModel):
    status: Status


class CreateStatusRequest(BaseModel):
    name: str
    category: StatusCategory
    sort_order: int


class UpdateStatusRequest(BaseModel):
    name: str | None = None
    category: StatusCategory | None = None
    sort_order: int | None = None
