from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from backend import schemas
from backend.api.dependencies import CurrentUser, Session
from backend.services import wiki_service

router = APIRouter(tags=["Wiki"])


@router.get(
    "/projects/{project_id}/wiki/pages",
    response_model=schemas.WikiPageTreeResponse,
)
async def list_wiki_pages(
    project_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    items = await wiki_service.list_pages_tree(
        session=session,
        project_id=project_id,
        current_user_id=current_user.id,
    )
    return {"items": items}


@router.post(
    "/projects/{project_id}/wiki/pages",
    status_code=201,
    response_model=schemas.WikiPageResponse,
)
async def create_wiki_page(
    project_id: UUID,
    body: schemas.CreateWikiPageRequest,
    session: Session,
    current_user: CurrentUser,
):
    page = await wiki_service.create_page(
        session=session,
        project_id=project_id,
        current_user_id=current_user.id,
        payload=body,
    )
    return {"page": page}


@router.get(
    "/projects/{project_id}/wiki/pages/{page_id}",
    response_model=schemas.WikiPageResponse,
)
async def get_wiki_page(
    project_id: UUID,
    page_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    page = await wiki_service.get_page(
        session=session,
        project_id=project_id,
        page_id=page_id,
        current_user_id=current_user.id,
    )
    return {"page": page}


@router.patch(
    "/projects/{project_id}/wiki/pages/{page_id}",
    response_model=schemas.WikiPageResponse,
)
async def update_wiki_page(
    project_id: UUID,
    page_id: UUID,
    body: schemas.UpdateWikiPageRequest,
    session: Session,
    current_user: CurrentUser,
):
    page = await wiki_service.update_page(
        session=session,
        project_id=project_id,
        page_id=page_id,
        current_user_id=current_user.id,
        payload=body,
    )
    return {"page": page}


@router.delete("/projects/{project_id}/wiki/pages/{page_id}", status_code=204)
async def delete_wiki_page(
    project_id: UUID,
    page_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    await wiki_service.delete_page(
        session=session,
        project_id=project_id,
        page_id=page_id,
        current_user_id=current_user.id,
    )


@router.get(
    "/projects/{project_id}/wiki/pages/{page_id}/revisions",
    response_model=schemas.WikiPageRevisionListResponse,
)
async def list_wiki_page_revisions(
    project_id: UUID,
    page_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    items = await wiki_service.list_revisions(
        session=session,
        project_id=project_id,
        page_id=page_id,
        current_user_id=current_user.id,
    )
    return {"items": items}


@router.post(
    "/projects/{project_id}/wiki/pages/{page_id}/restore",
    response_model=schemas.WikiPageResponse,
)
async def restore_wiki_page_revision(
    project_id: UUID,
    page_id: UUID,
    body: schemas.RestoreWikiPageRequest,
    session: Session,
    current_user: CurrentUser,
):
    page = await wiki_service.rollback_to_revision(
        session=session,
        project_id=project_id,
        page_id=page_id,
        version=body.version,
        current_user_id=current_user.id,
    )
    return {"page": page}


@router.post(
    "/projects/{project_id}/wiki/render",
    response_model=schemas.RenderWikiContentResponse,
)
async def render_wiki_content(
    project_id: UUID,
    body: schemas.RenderWikiContentRequest,
    session: Session,
    current_user: CurrentUser,
):
    rendered_html = await wiki_service.render_content(
        session=session,
        project_id=project_id,
        current_user_id=current_user.id,
        markdown_text=body.content_md,
    )
    return {"rendered_html": rendered_html}


@router.post(
    "/projects/{project_id}/wiki/pages/{page_id}/attachments/prepare",
    response_model=schemas.PrepareWikiAttachmentResponse,
)
async def prepare_wiki_page_attachment(
    project_id: UUID,
    page_id: UUID,
    body: schemas.PrepareWikiAttachmentRequest,
    session: Session,
    current_user: CurrentUser,
):
    return await wiki_service.prepare_attachment_upload(
        session=session,
        project_id=project_id,
        page_id=page_id,
        current_user_id=current_user.id,
        payload=body,
    )


@router.post(
    "/projects/{project_id}/wiki/pages/{page_id}/attachments",
    status_code=201,
    response_model=schemas.WikiPageAttachmentResponse,
)
async def create_wiki_page_attachment(
    project_id: UUID,
    page_id: UUID,
    body: schemas.CreateWikiAttachmentRequest,
    session: Session,
    current_user: CurrentUser,
):
    attachment = await wiki_service.create_attachment(
        session=session,
        project_id=project_id,
        page_id=page_id,
        current_user_id=current_user.id,
        payload=body,
    )
    return {"attachment": attachment}


@router.get(
    "/projects/{project_id}/wiki/pages/{page_id}/attachments",
    response_model=schemas.WikiPageAttachmentListResponse,
)
async def list_wiki_page_attachments(
    project_id: UUID,
    page_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    items = await wiki_service.list_attachments(
        session=session,
        project_id=project_id,
        page_id=page_id,
        current_user_id=current_user.id,
    )
    return {"items": items}


@router.get(
    "/wiki/attachments/{attachment_id}/download",
    response_model=schemas.WikiAttachmentDownloadResponse,
)
async def get_wiki_attachment_download_url(
    attachment_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    download_url = await wiki_service.generate_attachment_download_url(
        session=session,
        attachment_id=attachment_id,
        current_user_id=current_user.id,
    )
    return {"download_url": download_url}


@router.delete("/wiki/attachments/{attachment_id}", status_code=204)
async def delete_wiki_attachment(
    attachment_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    await wiki_service.delete_attachment(
        session=session,
        attachment_id=attachment_id,
        current_user_id=current_user.id,
    )
