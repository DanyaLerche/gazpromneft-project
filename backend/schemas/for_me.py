# Схемы страницы "For Me" из OpenAPI (/for-me).
from __future__ import annotations

from datetime import datetime
from typing import List, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.issue import Issue
from backend.schemas.project import ProjectResponse
from backend.schemas.status import Status
from backend.schemas.user import User


class ForMeFilters(BaseModel):
    model_config = ConfigDict(extra="ignore")

    statuses: List[Status]
    users: List[User]


class ForMeDigestItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    item_type: Literal["issue_updated", "new_comment"]
    issue_id: UUID
    issue_key: str
    issue_title: str
    project_id: UUID
    occurred_at: datetime
    summary: str


class ForMeDigest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    last_seen_timestamp: datetime | None = None
    generated_at: datetime
    items: List[ForMeDigestItem] = Field(default_factory=list)


class ForMeActionHistoryItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    action_type: Literal["issue_created", "comment_added", "worklog_added"]
    issue_id: UUID
    issue_key: str
    issue_title: str
    project_id: UUID
    occurred_at: datetime
    summary: str


class ForMeActionHistory(BaseModel):
    model_config = ConfigDict(extra="ignore")

    items: List[ForMeActionHistoryItem] = Field(default_factory=list)


class ForMeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    issues: List[Issue]
    projects: List[ProjectResponse]
    total: int
    filters: ForMeFilters
    mini_digest: ForMeDigest
    action_history: ForMeActionHistory
