# Схемы планового графика из OpenAPI (/users/{userId}/schedules, /projects/{projectId}/schedules).
from __future__ import annotations

from datetime import date, datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.issue import UserLite


class Schedule(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: UUID
    user_id: UUID
    date: date
    planned_hours: float | None = None
    comment: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ScheduleWithUser(Schedule):
    user: UserLite


class CreateScheduleRequest(BaseModel):
    date: date
    planned_hours: float = Field(..., ge=0)
    comment: str | None = None


class UpdateScheduleRequest(BaseModel):
    planned_hours: float | None = Field(None, ge=0)
    comment: str | None = None


class ScheduleResponse(BaseModel):
    schedule: Schedule


class PagedSchedules(BaseModel):
    items: List[Schedule]
    total: int


class PagedSchedulesWithUser(BaseModel):
    items: List[ScheduleWithUser]
    total: int
