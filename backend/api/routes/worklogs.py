from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query

from backend import schemas
from backend.api.dependencies import CurrentUser, Session
from backend.services import worklogs_service

router = APIRouter(tags=["Worklogs"])


@router.post("/issues/{issue_id}/worklogs", status_code=201, response_model=schemas.WorklogResponse)
async def create_worklog(
    issue_id: UUID,
    body: schemas.CreateWorklogRequest,
    session: Session,
    current_user: CurrentUser,
):
    worklog = await worklogs_service.create_issue_worklog(
        session=session,
        issue_id=issue_id,
        actor_id=current_user.id,
        payload=body,
    )
    return {"worklog": worklogs_service.to_worklog_schema(worklog)}


@router.get("/issues/{issue_id}/worklogs", response_model=schemas.PagedWorklogsWithSummary)
async def list_issue_worklogs(
    issue_id: UUID,
    session: Session,
    current_user: CurrentUser,
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    result = await worklogs_service.list_issue_worklogs(
        session=session,
        issue_id=issue_id,
        actor_id=current_user.id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return schemas.PagedWorklogsWithSummary(
        items=[worklogs_service.to_worklog_schema(item) for item in result.items],
        total=result.total,
        summary=schemas.WorklogSummary(
            planned_hours=result.planned_hours,
            logged_hours=result.logged_hours,
        ),
    )


@router.get("/users/{user_id}/worklogs", response_model=schemas.PagedWorklogs)
async def list_user_worklogs(
    user_id: UUID,
    session: Session,
    current_user: CurrentUser,
    project_id: UUID | None = None,
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    result = await worklogs_service.list_user_worklogs(
        session=session,
        user_id=user_id,
        actor_id=current_user.id,
        project_id=project_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return schemas.PagedWorklogs(
        items=[worklogs_service.to_worklog_schema(item) for item in result.items],
        total=result.total,
    )


@router.patch("/worklogs/{worklog_id}", response_model=schemas.WorklogResponse)
async def update_worklog(
    worklog_id: UUID,
    body: schemas.UpdateWorklogRequest,
    session: Session,
    current_user: CurrentUser,
):
    worklog = await worklogs_service.update_worklog(
        session=session,
        worklog_id=worklog_id,
        actor_id=current_user.id,
        payload=body,
    )
    return {"worklog": worklogs_service.to_worklog_schema(worklog)}


@router.delete("/worklogs/{worklog_id}", status_code=204)
async def delete_worklog(
    worklog_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    await worklogs_service.delete_worklog(
        session=session,
        worklog_id=worklog_id,
        actor_id=current_user.id,
    )
