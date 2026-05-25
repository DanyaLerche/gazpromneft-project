from __future__ import annotations

from datetime import date
from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.issue import WorklogSummary


class Worklog(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: UUID
    issue_id: UUID
    user_id: UUID
    work_date: date
    hours: float
    comment: str | None = None


class CreateWorklogRequest(BaseModel):
    work_date: date
    hours: float = Field(..., gt=0)
    comment: str | None = None


class UpdateWorklogRequest(BaseModel):
    work_date: date | None = None
    hours: float | None = Field(None, gt=0)
    comment: str | None = None


class WorklogResponse(BaseModel):
    worklog: Worklog


class PagedWorklogs(BaseModel):
    items: List[Worklog]
    total: int


class PagedWorklogsWithSummary(BaseModel):
    items: List[Worklog]
    total: int
    summary: WorklogSummary
