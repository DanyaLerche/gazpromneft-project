# Схемы задач/эпиков из OpenAPI (openapi-v0.1.0.yaml).
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.attachment import IssueAttachment


class IssueType(str, Enum):
    EPIC = "epic"
    TASK = "task"


class Issue(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: UUID
    project_id: UUID
    key: str
    type: IssueType
    title: str
    description: str | None = None
    status_id: UUID | None = None
    criticality_id: UUID | None = None
    author_id: UUID
    assignee_id: UUID | None = None
    parent_id: UUID | None = None
    start_date: date | None = None
    due_date: date | None = None
    taken_in_work_at: datetime | None = None
    resolved_at: datetime | None = None
    planned_hours: float | None = None
    logged_hours: float | None = None
    created_at: datetime
    updated_at: datetime


class CreateIssueRequest(BaseModel):
    type: IssueType
    title: str
    description: str | None = None
    status_id: UUID
    criticality_id: UUID | None = None
    assignee_id: UUID | None = None
    parent_id: UUID | None = None
    start_date: date | None = None
    due_date: date | None = None
    planned_hours: float | None = None


class UpdateIssueRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    status_id: UUID | None = None
    criticality_id: UUID | None = None
    assignee_id: UUID | None = None
    parent_id: UUID | None = None
    start_date: date | None = None
    due_date: date | None = None
    planned_hours: float | None = None


class PagedIssues(BaseModel):
    items: List[Issue]
    total: int


class IssueResponse(BaseModel):
    issue: Issue


class UserLite(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    full_name: str


class WorklogSummary(BaseModel):
    planned_hours: float | None = None
    logged_hours: float | None = None


class IssueComment(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    issue_id: UUID
    author_id: UUID
    body: str
    created_at: str
    updated_at: str


class IssueDetailsResponse(BaseModel):
    issue: Issue
    watchers: List[UserLite] = []
    comments: List[IssueComment] = []
    attachments: List[IssueAttachment] = []
    worklog_summary: WorklogSummary = Field(default_factory=lambda: WorklogSummary())
