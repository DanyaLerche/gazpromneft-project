# Схемы вложений задачи (OpenAPI: Attachments).
from __future__ import annotations

from datetime import datetime
from typing import Dict, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IssueAttachment(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: UUID
    issue_id: UUID
    uploaded_by: UUID
    file_name: str
    mime_type: str | None = None
    size_bytes: int
    storage_key: str
    created_at: datetime


class PrepareAttachmentRequest(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=1024)
    mime_type: str = Field(..., min_length=1, max_length=255)
    size_bytes: int = Field(..., ge=1)


class PresignedUpload(BaseModel):
    storage_key: str
    upload_url: str
    headers: Dict[str, str] = Field(default_factory=dict)
    fields: Dict[str, str] = Field(default_factory=dict)
    method: str = "POST"
    expires_in: int


class PrepareAttachmentResponse(BaseModel):
    upload: PresignedUpload


class CreateAttachmentRequest(BaseModel):
    storage_key: str = Field(..., min_length=1)
    file_name: str = Field(..., min_length=1, max_length=1024)
    mime_type: str = Field(..., min_length=1, max_length=255)
    size_bytes: int = Field(..., ge=1)


class AttachmentResponse(BaseModel):
    attachment: IssueAttachment


class AttachmentListResponse(BaseModel):
    items: List[IssueAttachment]


class AttachmentDownloadResponse(BaseModel):
    download_url: str
