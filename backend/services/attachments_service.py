from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID, uuid4

import aioboto3
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import schemas
from backend.models import Issue, IssueAttachment
from backend.services import access_control
from config import settings

logger = logging.getLogger(__name__)


def _sanitize_file_name(file_name: str) -> str:
    # Оставляем только имя файла, чтобы исключить path traversal.
    return Path(file_name).name.strip() or "file"


def build_storage_key(issue_id: UUID, file_name: str) -> str:
    safe_name = _sanitize_file_name(file_name)
    return f"issues/{issue_id}/{uuid4()}-{safe_name}"


async def _get_issue_or_404(session: AsyncSession, issue_id: UUID) -> Issue:
    issue = (await session.execute(select(Issue).where(Issue.id == issue_id))).scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue


async def _get_attachment_or_404(session: AsyncSession, attachment_id: UUID) -> IssueAttachment:
    attachment = (
        await session.execute(select(IssueAttachment).where(IssueAttachment.id == attachment_id))
    ).scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return attachment


async def _ensure_project_access(session: AsyncSession, project_id: UUID, user_id: UUID) -> None:
    await access_control.ensure_project_access(session, project_id, user_id)


def _build_s3_client(*, endpoint_url: str | None = None):
    access_key = settings.S3_ACCESS_KEY or settings.S3_ACCESS_KEY_ID or None
    secret_key = settings.S3_SECRET_KEY or settings.S3_SECRET_ACCESS_KEY or None
    return aioboto3.Session().client(
        "s3",
        endpoint_url=endpoint_url or settings.S3_ENDPOINT_URL,
        region_name=settings.S3_REGION,
        use_ssl=settings.S3_USE_SSL,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )


def _get_public_s3_endpoint_url() -> str | None:
    # For browser-based uploads/downloads we must return a URL reachable from the client,
    # which may differ from the internal endpoint used by backend containers.
    return settings.S3_PUBLIC_ENDPOINT_URL or settings.S3_ENDPOINT_URL


async def prepare_upload(
    session: AsyncSession,
    issue_id: UUID,
    current_user_id: UUID,
    payload: schemas.PrepareAttachmentRequest,
) -> schemas.PrepareAttachmentResponse:
    issue = await _get_issue_or_404(session, issue_id)
    await _ensure_project_access(session, issue.project_id, current_user_id)

    storage_key = build_storage_key(issue_id, payload.file_name)
    async with _build_s3_client(endpoint_url=_get_public_s3_endpoint_url()) as s3_client:
        post = await s3_client.generate_presigned_post(
            Bucket=settings.S3_BUCKET_NAME,
            Key=storage_key,
            Fields={"Content-Type": payload.mime_type},
            Conditions=[
                {"Content-Type": payload.mime_type},
                ["content-length-range", 1, payload.size_bytes],
            ],
            ExpiresIn=settings.S3_PRESIGNED_UPLOAD_EXPIRES_SECONDS,
        )

    return schemas.PrepareAttachmentResponse(
        upload=schemas.PresignedUpload(
            storage_key=storage_key,
            upload_url=post["url"],
            fields=post.get("fields", {}),
            headers={},
            method="POST",
            expires_in=settings.S3_PRESIGNED_UPLOAD_EXPIRES_SECONDS,
        )
    )


async def create_attachment(
    session: AsyncSession,
    issue_id: UUID,
    current_user_id: UUID,
    payload: schemas.CreateAttachmentRequest,
) -> IssueAttachment:
    issue = await _get_issue_or_404(session, issue_id)
    await _ensure_project_access(session, issue.project_id, current_user_id)
    if not payload.storage_key.startswith(f"issues/{issue_id}/"):
        raise HTTPException(status_code=400, detail="storage_key does not belong to issue")

    async with _build_s3_client() as s3_client:
        try:
            await s3_client.head_object(Bucket=settings.S3_BUCKET_NAME, Key=payload.storage_key)
        except Exception:
            raise HTTPException(status_code=400, detail="Object not found in storage")

    attachment = IssueAttachment(
        issue_id=issue_id,
        uploaded_by=current_user_id,
        file_name=payload.file_name,
        mime_type=payload.mime_type,
        size_bytes=payload.size_bytes,
        storage_key=payload.storage_key,
    )
    session.add(attachment)
    await session.commit()
    await session.refresh(attachment)
    logger.info("attachment_created issue_id=%s attachment_id=%s", issue_id, attachment.id)
    return attachment


async def list_issue_attachments(
    session: AsyncSession,
    issue_id: UUID,
    current_user_id: UUID,
) -> list[IssueAttachment]:
    issue = await _get_issue_or_404(session, issue_id)
    await _ensure_project_access(session, issue.project_id, current_user_id)
    attachments = (
        await session.execute(
            select(IssueAttachment)
            .where(IssueAttachment.issue_id == issue_id)
            .order_by(IssueAttachment.created_at.desc())
        )
    ).scalars().all()
    return list(attachments)


async def generate_download_url(
    session: AsyncSession,
    attachment_id: UUID,
    current_user_id: UUID,
) -> str:
    attachment = await _get_attachment_or_404(session, attachment_id)
    issue = await _get_issue_or_404(session, attachment.issue_id)
    await _ensure_project_access(session, issue.project_id, current_user_id)

    async with _build_s3_client(endpoint_url=_get_public_s3_endpoint_url()) as s3_client:
        url = await s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": settings.S3_BUCKET_NAME,
                "Key": attachment.storage_key,
            },
            ExpiresIn=settings.S3_PRESIGNED_DOWNLOAD_EXPIRES_SECONDS,
        )
    return url


async def delete_attachment(
    session: AsyncSession,
    attachment_id: UUID,
    current_user_id: UUID,
) -> None:
    attachment = await _get_attachment_or_404(session, attachment_id)
    issue = await _get_issue_or_404(session, attachment.issue_id)
    await _ensure_project_access(session, issue.project_id, current_user_id)

    async with _build_s3_client() as s3_client:
        await s3_client.delete_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=attachment.storage_key,
        )

    await session.delete(attachment)
    await session.commit()
    logger.info("attachment_deleted attachment_id=%s", attachment_id)
