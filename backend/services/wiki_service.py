from __future__ import annotations

import logging
import re
from pathlib import Path
from uuid import UUID, uuid4

import aioboto3
import markdown
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import schemas
from backend.models import Project, WikiPage, WikiPageAttachment, WikiPageRevision
from backend.services import access_control
from config import settings

logger = logging.getLogger(__name__)


MACRO_INFO_RE = re.compile(r"\{info\}(.*?)\{info\}", re.IGNORECASE | re.DOTALL)
MACRO_WARNING_RE = re.compile(r"\{warning\}(.*?)\{warning\}", re.IGNORECASE | re.DOTALL)
MACRO_CODE_RE = re.compile(
    r"\{code(?::([^}]+))?\}(.*?)\{code\}", re.IGNORECASE | re.DOTALL
)
MACRO_INCLUDE_RE = re.compile(r"\{include:([a-z0-9\-_]+)\}", re.IGNORECASE)


def _sanitize_file_name(file_name: str) -> str:
    return Path(file_name).name.strip() or "file"


def build_wiki_storage_key(page_id: UUID, file_name: str) -> str:
    safe_name = _sanitize_file_name(file_name)
    return f"wiki-pages/{page_id}/{uuid4()}-{safe_name}"


def _render_markdown_with_macros(markdown_text: str) -> str:
    content = markdown_text or ""

    content = MACRO_INFO_RE.sub(
        lambda match: f"\n<div class=\"confluence-macro info\">\n{match.group(1).strip()}\n</div>\n",
        content,
    )
    content = MACRO_WARNING_RE.sub(
        lambda match: f"\n<div class=\"confluence-macro warning\">\n{match.group(1).strip()}\n</div>\n",
        content,
    )
    content = MACRO_CODE_RE.sub(
        lambda match: (
            "\n<pre class=\"confluence-macro code\">"
            f"<code data-language=\"{(match.group(1) or '').strip()}\">"
            f"{match.group(2).strip()}"
            "</code></pre>\n"
        ),
        content,
    )
    content = MACRO_INCLUDE_RE.sub(
        lambda match: (
            "\n<div class=\"confluence-macro include\""
            f" data-target=\"{match.group(1).strip()}\">"
            f"Включение страницы: {match.group(1).strip()}</div>\n"
        ),
        content,
    )

    return markdown.markdown(
        content,
        extensions=["extra", "tables", "sane_lists", "fenced_code"],
    )


async def _ensure_project_access(session: AsyncSession, project_id: UUID, user_id: UUID) -> Project:
    return await access_control.ensure_project_access(session, project_id, user_id)


async def _get_page_or_404(session: AsyncSession, page_id: UUID) -> WikiPage:
    page = (await session.execute(select(WikiPage).where(WikiPage.id == page_id))).scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Wiki page not found")
    return page


async def _get_page_in_project_or_404(
    session: AsyncSession,
    project_id: UUID,
    page_id: UUID,
) -> WikiPage:
    page = (
        await session.execute(
            select(WikiPage).where(
                WikiPage.id == page_id,
                WikiPage.project_id == project_id,
            )
        )
    ).scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Wiki page not found")
    return page


async def _validate_parent_page(
    session: AsyncSession,
    project_id: UUID,
    parent_id: UUID | None,
    *,
    current_page_id: UUID | None = None,
) -> UUID | None:
    if parent_id is None:
        return None

    parent = await _get_page_in_project_or_404(session, project_id, parent_id)
    if current_page_id and parent.id == current_page_id:
        raise HTTPException(status_code=400, detail="Page cannot be parent of itself")

    if current_page_id:
        cursor: WikiPage | None = parent
        while cursor is not None:
            if cursor.id == current_page_id:
                raise HTTPException(status_code=400, detail="Cycle in page hierarchy")
            if cursor.parent_id is None:
                break
            cursor = (
                await session.execute(
                    select(WikiPage).where(WikiPage.id == cursor.parent_id)
                )
            ).scalar_one_or_none()

    return parent.id


def _build_tree(items: list[WikiPage]) -> list[schemas.WikiPageTreeItem]:
    nodes: dict[UUID, schemas.WikiPageTreeItem] = {}
    roots: list[schemas.WikiPageTreeItem] = []

    for page in items:
        nodes[page.id] = schemas.WikiPageTreeItem(
            id=page.id,
            project_id=page.project_id,
            parent_id=page.parent_id,
            title=page.title,
            version=page.version,
            updated_at=page.updated_at,
            children=[],
        )

    for page in items:
        node = nodes[page.id]
        if page.parent_id and page.parent_id in nodes:
            nodes[page.parent_id].children.append(node)
        else:
            roots.append(node)

    def _sort_recursive(branch: list[schemas.WikiPageTreeItem]) -> None:
        branch.sort(key=lambda item: item.title.lower())
        for child in branch:
            _sort_recursive(child.children)

    _sort_recursive(roots)
    return roots


async def list_pages_tree(
    session: AsyncSession,
    project_id: UUID,
    current_user_id: UUID,
) -> list[schemas.WikiPageTreeItem]:
    await _ensure_project_access(session, project_id, current_user_id)
    pages = (
        await session.execute(
            select(WikiPage)
            .where(WikiPage.project_id == project_id)
            .order_by(WikiPage.updated_at.desc())
        )
    ).scalars().all()
    return _build_tree(list(pages))


async def get_page(
    session: AsyncSession,
    project_id: UUID,
    page_id: UUID,
    current_user_id: UUID,
) -> WikiPage:
    await _ensure_project_access(session, project_id, current_user_id)
    return await _get_page_in_project_or_404(session, project_id, page_id)


async def create_page(
    session: AsyncSession,
    project_id: UUID,
    current_user_id: UUID,
    payload: schemas.CreateWikiPageRequest,
) -> WikiPage:
    await _ensure_project_access(session, project_id, current_user_id)
    parent_id = await _validate_parent_page(session, project_id, payload.parent_id)

    rendered_html = _render_markdown_with_macros(payload.content_md)
    page = WikiPage(
        project_id=project_id,
        parent_id=parent_id,
        title=payload.title.strip(),
        content_md=payload.content_md,
        rendered_html=rendered_html,
        version=1,
        created_by=current_user_id,
        updated_by=current_user_id,
    )
    session.add(page)
    await session.flush()

    revision = WikiPageRevision(
        page_id=page.id,
        project_id=project_id,
        parent_id=parent_id,
        version=1,
        title=page.title,
        content_md=page.content_md,
        rendered_html=page.rendered_html,
        created_by=current_user_id,
    )
    session.add(revision)
    await session.commit()
    await session.refresh(page)
    logger.info("wiki_page_created project_id=%s page_id=%s", project_id, page.id)
    return page


async def render_markdown_preview(
    session: AsyncSession,
    project_id: UUID,
    current_user_id: UUID,
    markdown_text: str,
) -> str:
    await _ensure_project_access(session, project_id, current_user_id)
    return _render_markdown_with_macros(markdown_text)


async def render_content(
    session: AsyncSession,
    project_id: UUID,
    current_user_id: UUID,
    markdown_text: str,
) -> str:
    return await render_markdown_preview(
        session=session,
        project_id=project_id,
        current_user_id=current_user_id,
        markdown_text=markdown_text,
    )


async def update_page(
    session: AsyncSession,
    project_id: UUID,
    page_id: UUID,
    current_user_id: UUID,
    payload: schemas.UpdateWikiPageRequest,
) -> WikiPage:
    await _ensure_project_access(session, project_id, current_user_id)
    page = await _get_page_in_project_or_404(session, project_id, page_id)

    fields_set = payload.model_fields_set

    new_parent_id = page.parent_id
    if "parent_id" in fields_set:
        new_parent_id = await _validate_parent_page(
            session,
            project_id,
            payload.parent_id,
            current_page_id=page.id,
        )

    new_title = page.title
    if "title" in fields_set and payload.title is not None:
        new_title = payload.title.strip()

    new_content_md = page.content_md
    if "content_md" in fields_set and payload.content_md is not None:
        new_content_md = payload.content_md

    changed = (
        new_parent_id != page.parent_id
        or new_title != page.title
        or new_content_md != page.content_md
    )
    if not changed:
        return page

    page.parent_id = new_parent_id
    page.title = new_title
    page.content_md = new_content_md
    page.rendered_html = _render_markdown_with_macros(new_content_md)
    page.version += 1
    page.updated_by = current_user_id

    session.add(
        WikiPageRevision(
            page_id=page.id,
            project_id=project_id,
            parent_id=page.parent_id,
            version=page.version,
            title=page.title,
            content_md=page.content_md,
            rendered_html=page.rendered_html,
            created_by=current_user_id,
        )
    )

    await session.commit()
    await session.refresh(page)
    logger.info("wiki_page_updated page_id=%s version=%s", page.id, page.version)
    return page


async def delete_page(
    session: AsyncSession,
    project_id: UUID,
    page_id: UUID,
    current_user_id: UUID,
) -> None:
    await _ensure_project_access(session, project_id, current_user_id)
    page = await _get_page_in_project_or_404(session, project_id, page_id)
    await session.delete(page)
    await session.commit()
    logger.info("wiki_page_deleted page_id=%s", page.id)


async def list_revisions(
    session: AsyncSession,
    project_id: UUID,
    page_id: UUID,
    current_user_id: UUID,
) -> list[WikiPageRevision]:
    await _ensure_project_access(session, project_id, current_user_id)
    await _get_page_in_project_or_404(session, project_id, page_id)
    revisions = (
        await session.execute(
            select(WikiPageRevision)
            .where(
                WikiPageRevision.project_id == project_id,
                WikiPageRevision.page_id == page_id,
            )
            .order_by(WikiPageRevision.version.desc())
        )
    ).scalars().all()
    return list(revisions)


async def rollback_to_revision(
    session: AsyncSession,
    project_id: UUID,
    page_id: UUID,
    version: int,
    current_user_id: UUID,
) -> WikiPage:
    await _ensure_project_access(session, project_id, current_user_id)
    page = await _get_page_in_project_or_404(session, project_id, page_id)

    revision = (
        await session.execute(
            select(WikiPageRevision).where(
                WikiPageRevision.project_id == project_id,
                WikiPageRevision.page_id == page_id,
                WikiPageRevision.version == version,
            )
        )
    ).scalar_one_or_none()
    if not revision:
        raise HTTPException(status_code=404, detail="Revision not found")

    page.parent_id = revision.parent_id
    page.title = revision.title
    page.content_md = revision.content_md
    page.rendered_html = revision.rendered_html
    page.version += 1
    page.updated_by = current_user_id

    session.add(
        WikiPageRevision(
            page_id=page.id,
            project_id=project_id,
            parent_id=page.parent_id,
            version=page.version,
            title=page.title,
            content_md=page.content_md,
            rendered_html=page.rendered_html,
            created_by=current_user_id,
        )
    )

    await session.commit()
    await session.refresh(page)
    logger.info("wiki_page_rollback page_id=%s to=%s new=%s", page.id, version, page.version)
    return page


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
    return settings.S3_PUBLIC_ENDPOINT_URL or settings.S3_ENDPOINT_URL


async def prepare_attachment_upload(
    session: AsyncSession,
    project_id: UUID,
    page_id: UUID,
    current_user_id: UUID,
    payload: schemas.PrepareWikiAttachmentRequest,
) -> schemas.PrepareWikiAttachmentResponse:
    await _ensure_project_access(session, project_id, current_user_id)
    await _get_page_in_project_or_404(session, project_id, page_id)

    storage_key = build_wiki_storage_key(page_id, payload.file_name)
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

    return schemas.PrepareWikiAttachmentResponse(
        upload={
            "storage_key": storage_key,
            "upload_url": post["url"],
            "fields": post.get("fields", {}),
            "headers": {},
            "method": "POST",
            "expires_in": settings.S3_PRESIGNED_UPLOAD_EXPIRES_SECONDS,
        }
    )


async def create_attachment(
    session: AsyncSession,
    project_id: UUID,
    page_id: UUID,
    current_user_id: UUID,
    payload: schemas.CreateWikiAttachmentRequest,
) -> WikiPageAttachment:
    await _ensure_project_access(session, project_id, current_user_id)
    await _get_page_in_project_or_404(session, project_id, page_id)
    if not payload.storage_key.startswith(f"wiki-pages/{page_id}/"):
        raise HTTPException(status_code=400, detail="storage_key does not belong to wiki page")

    async with _build_s3_client() as s3_client:
        try:
            await s3_client.head_object(Bucket=settings.S3_BUCKET_NAME, Key=payload.storage_key)
        except Exception:
            raise HTTPException(status_code=400, detail="Object not found in storage")

    attachment = WikiPageAttachment(
        page_id=page_id,
        uploaded_by=current_user_id,
        file_name=payload.file_name,
        mime_type=payload.mime_type,
        size_bytes=payload.size_bytes,
        storage_key=payload.storage_key,
    )
    session.add(attachment)
    await session.commit()
    await session.refresh(attachment)
    return attachment


async def list_attachments(
    session: AsyncSession,
    project_id: UUID,
    page_id: UUID,
    current_user_id: UUID,
) -> list[WikiPageAttachment]:
    await _ensure_project_access(session, project_id, current_user_id)
    await _get_page_in_project_or_404(session, project_id, page_id)
    attachments = (
        await session.execute(
            select(WikiPageAttachment)
            .where(WikiPageAttachment.page_id == page_id)
            .order_by(WikiPageAttachment.created_at.desc())
        )
    ).scalars().all()
    return list(attachments)


async def generate_attachment_download_url(
    session: AsyncSession,
    attachment_id: UUID,
    current_user_id: UUID,
) -> str:
    attachment = (
        await session.execute(
            select(WikiPageAttachment).where(WikiPageAttachment.id == attachment_id)
        )
    ).scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    page = await _get_page_or_404(session, attachment.page_id)
    await _ensure_project_access(session, page.project_id, current_user_id)

    async with _build_s3_client(endpoint_url=_get_public_s3_endpoint_url()) as s3_client:
        return await s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": settings.S3_BUCKET_NAME,
                "Key": attachment.storage_key,
            },
            ExpiresIn=settings.S3_PRESIGNED_DOWNLOAD_EXPIRES_SECONDS,
        )


async def delete_attachment(
    session: AsyncSession,
    attachment_id: UUID,
    current_user_id: UUID,
) -> None:
    attachment = (
        await session.execute(
            select(WikiPageAttachment).where(WikiPageAttachment.id == attachment_id)
        )
    ).scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    page = await _get_page_or_404(session, attachment.page_id)
    await _ensure_project_access(session, page.project_id, current_user_id)

    async with _build_s3_client() as s3_client:
        await s3_client.delete_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=attachment.storage_key,
        )

    await session.delete(attachment)
    await session.commit()
