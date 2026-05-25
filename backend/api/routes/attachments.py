# Эндпоинты вложений задач (S3 presigned upload/download).
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from backend import schemas
from backend.api.dependencies import CurrentUser, Session
from backend.services import attachments_service

router = APIRouter(tags=["Attachments"])


@router.post(
    "/issues/{issue_id}/attachments/prepare",
    response_model=schemas.PrepareAttachmentResponse,
)
async def prepare_attachment(
    issue_id: UUID,
    body: schemas.PrepareAttachmentRequest,
    session: Session,
    current_user: CurrentUser,
):
    return await attachments_service.prepare_upload(
        session=session,
        issue_id=issue_id,
        current_user_id=current_user.id,
        payload=body,
    )


@router.post(
    "/issues/{issue_id}/attachments",
    status_code=201,
    response_model=schemas.AttachmentResponse,
)
async def create_attachment(
    issue_id: UUID,
    body: schemas.CreateAttachmentRequest,
    session: Session,
    current_user: CurrentUser,
):
    attachment = await attachments_service.create_attachment(
        session=session,
        issue_id=issue_id,
        current_user_id=current_user.id,
        payload=body,
    )
    return {"attachment": attachment}


@router.get(
    "/issues/{issue_id}/attachments",
    response_model=schemas.AttachmentListResponse,
)
async def list_attachments(
    issue_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    items = await attachments_service.list_issue_attachments(
        session=session,
        issue_id=issue_id,
        current_user_id=current_user.id,
    )
    return {"items": items}


@router.get(
    "/attachments/{attachment_id}/download",
    response_model=schemas.AttachmentDownloadResponse,
)
async def get_attachment_download_url(
    attachment_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    download_url = await attachments_service.generate_download_url(
        session=session,
        attachment_id=attachment_id,
        current_user_id=current_user.id,
    )
    return {"download_url": download_url}


@router.delete("/attachments/{attachment_id}", status_code=204)
async def delete_attachment(
    attachment_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    await attachments_service.delete_attachment(
        session=session,
        attachment_id=attachment_id,
        current_user_id=current_user.id,
    )
