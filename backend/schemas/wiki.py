from __future__ import annotations

from datetime import datetime
from typing import Dict, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WikiPage(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: UUID
    project_id: UUID
    parent_id: UUID | None = None
    title: str
    content_md: str
    rendered_html: str
    version: int
    created_by: UUID
    updated_by: UUID
    created_at: datetime
    updated_at: datetime


class WikiPageTreeItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: UUID
    project_id: UUID
    parent_id: UUID | None = None
    title: str
    version: int
    updated_at: datetime
    children: List["WikiPageTreeItem"] = Field(default_factory=list)


class WikiPageRevision(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: UUID
    page_id: UUID
    project_id: UUID
    parent_id: UUID | None = None
    version: int
    title: str
    content_md: str
    rendered_html: str
    created_by: UUID
    created_at: datetime


class WikiPageAttachment(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: UUID
    page_id: UUID
    uploaded_by: UUID
    file_name: str
    mime_type: str | None = None
    size_bytes: int
    storage_key: str
    created_at: datetime


class PresignedUpload(BaseModel):
    storage_key: str
    upload_url: str
    headers: Dict[str, str] = Field(default_factory=dict)
    fields: Dict[str, str] = Field(default_factory=dict)
    method: str = "POST"
    expires_in: int


class CreateWikiPageRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content_md: str = Field(default="")
    parent_id: UUID | None = None


class UpdateWikiPageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=255)
    content_md: str | None = None
    parent_id: UUID | None = None


class RestoreWikiPageRequest(BaseModel):
    version: int = Field(..., ge=1)


class RenderWikiContentRequest(BaseModel):
    content_md: str = Field(default="")


class RenderWikiContentResponse(BaseModel):
    rendered_html: str


class PrepareWikiAttachmentRequest(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=1024)
    mime_type: str = Field(..., min_length=1, max_length=255)
    size_bytes: int = Field(..., ge=1)


class CreateWikiAttachmentRequest(BaseModel):
    storage_key: str = Field(..., min_length=1)
    file_name: str = Field(..., min_length=1, max_length=1024)
    mime_type: str = Field(..., min_length=1, max_length=255)
    size_bytes: int = Field(..., ge=1)


class WikiPageResponse(BaseModel):
    page: WikiPage


class WikiPageTreeResponse(BaseModel):
    items: List[WikiPageTreeItem]


class WikiPageRevisionListResponse(BaseModel):
    items: List[WikiPageRevision]


class WikiPageAttachmentResponse(BaseModel):
    attachment: WikiPageAttachment


class WikiPageAttachmentListResponse(BaseModel):
    items: List[WikiPageAttachment]


class PrepareWikiAttachmentResponse(BaseModel):
    upload: PresignedUpload


class WikiAttachmentDownloadResponse(BaseModel):
    download_url: str


WikiPageTreeItem.model_rebuild()
