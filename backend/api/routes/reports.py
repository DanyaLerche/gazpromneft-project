from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from html import escape
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query, Response
from sqlalchemy import func, select

from backend import schemas
from backend.api.dependencies import CurrentUser, Session
from backend.models import Issue, ProjectUser, Status, User, Worklog
from backend.services import access_control

router = APIRouter(tags=["Reports"])

UNASSIGNED_KEY = "__unassigned__"
UNASSIGNED_NAME = "Без исполнителя"
EXPORT_COLUMNS = ("section", "entity", "metric", "value")


def _to_float(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _percent(actual: float, planned: float) -> float | None:
    if planned <= 0:
        return None
    return round((actual / planned) * 100, 2)


def _variance(actual: float, planned: float) -> float:
    return round(actual - planned, 2)


def _serialize_export_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return str(value)


def _build_dashboard_export_rows(
    report: schemas.ProjectDashboardReportResponse,
) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = [
        ("meta", "project", "project_id", _serialize_export_value(report.project_id)),
        ("meta", "project", "generated_at", _serialize_export_value(report.generated_at)),
    ]

    for metric, value in (
        ("completed", report.task_summary.completed),
        ("in_progress", report.task_summary.in_progress),
        ("not_started", report.task_summary.not_started),
        ("total", report.task_summary.total),
    ):
        rows.append(("task_summary", "project", metric, _serialize_export_value(value)))

    for item in report.tasks_by_assignee:
        entity = item.assignee_name
        for metric, value in (
            ("completed", item.completed),
            ("in_progress", item.in_progress),
            ("not_started", item.not_started),
            ("total", item.total),
        ):
            rows.append(("tasks_by_assignee", entity, metric, _serialize_export_value(value)))

    for metric, value in (
        ("planned_hours", report.effort_summary.planned_hours),
        ("actual_hours", report.effort_summary.actual_hours),
        ("variance_hours", report.effort_summary.variance_hours),
        ("actual_vs_plan_percent", report.effort_summary.actual_vs_plan_percent),
    ):
        rows.append(("effort_summary", "project", metric, _serialize_export_value(value)))

    for item in report.effort_by_assignee:
        entity = item.assignee_name
        for metric, value in (
            ("planned_hours", item.planned_hours),
            ("actual_hours", item.actual_hours),
            ("variance_hours", item.variance_hours),
            ("actual_vs_plan_percent", item.actual_vs_plan_percent),
        ):
            rows.append(("effort_by_assignee", entity, metric, _serialize_export_value(value)))

    for item in report.status_distribution:
        rows.append(
            (
                "status_distribution",
                item.status_name,
                "tasks_count",
                _serialize_export_value(item.tasks_count),
            )
        )

    rows.append(
        (
            "overdue_summary",
            "project",
            "total_overdue_tasks",
            _serialize_export_value(report.overdue.total_overdue_tasks),
        )
    )
    for item in report.overdue.overdue_by_assignee:
        rows.append(
            (
                "overdue_by_assignee",
                item.assignee_name,
                "tasks_count",
                _serialize_export_value(item.tasks_count),
            )
        )

    for item in report.overdue.tasks:
        entity = f"{item.issue_key} — {item.title}"
        for metric, value in (
            ("assignee_name", item.assignee_name),
            ("due_date", item.due_date),
            ("status_name", item.status_name),
            ("days_overdue", item.days_overdue),
        ):
            rows.append(("overdue_tasks", entity, metric, _serialize_export_value(value)))

    for item in report.workload:
        entity = item.assignee_name
        for metric, value in (
            ("open_tasks", item.open_tasks),
            ("planned_hours_open_tasks", item.planned_hours_open_tasks),
        ):
            rows.append(("workload", entity, metric, _serialize_export_value(value)))

    recent_entity = f"last_{report.recent_activity.days}_days"
    for metric, value in (
        ("created_tasks", report.recent_activity.created_tasks),
        ("completed_tasks", report.recent_activity.completed_tasks),
        ("logged_hours", report.recent_activity.logged_hours),
        ("completion_to_creation_percent", report.recent_activity.completion_to_creation_percent),
    ):
        rows.append(("recent_activity", recent_entity, metric, _serialize_export_value(value)))

    return rows


def _build_dashboard_csv(rows: list[tuple[str, str, str, str]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(EXPORT_COLUMNS)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def _build_dashboard_excel(rows: list[tuple[str, str, str, str]]) -> bytes:
    header_html = "".join(f"<th>{escape(column)}</th>" for column in EXPORT_COLUMNS)
    rows_html = "".join(
        "<tr>"
        + "".join(f"<td>{escape(value)}</td>" for value in row)
        + "</tr>"
        for row in rows
    )
    html_content = (
        "<html><head><meta charset='utf-8'></head><body>"
        "<table border='1'>"
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        "</table></body></html>"
    )
    return html_content.encode("utf-8-sig")


async def _build_project_dashboard_report(
    project_id: UUID,
    session: Session,
    current_user: CurrentUser,
    recent_days: int,
    overdue_limit: int,
) -> schemas.ProjectDashboardReportResponse:
    await access_control.ensure_project_admin_context(
        session,
        project_id,
        current_user.id,
        current_user=current_user,
    )

    statuses = (
        await session.execute(
            select(Status).where(Status.project_id == project_id).order_by(Status.sort_order.asc())
        )
    ).scalars().all()
    status_by_id = {status.id: status for status in statuses}

    task_rows = (
        await session.execute(
            select(
                Issue.id,
                Issue.key,
                Issue.title,
                Issue.assignee_id,
                Issue.status_id,
                Issue.due_date,
                Issue.created_at,
                Issue.resolved_at,
                Issue.planned_hours,
            ).where(
                Issue.project_id == project_id,
                Issue.type == schemas.IssueType.TASK.value,
            )
        )
    ).all()

    participants = (
        await session.execute(
            select(ProjectUser.user_id, User.full_name)
            .join(User, User.id == ProjectUser.user_id)
            .where(ProjectUser.project_id == project_id)
        )
    ).all()

    participant_names: dict[str, str] = {str(user_id): full_name for user_id, full_name in participants}
    assignee_ids = {str(row.assignee_id) for row in task_rows if row.assignee_id is not None}

    worklog_rows = (
        await session.execute(
            select(Worklog.user_id, func.coalesce(func.sum(Worklog.hours), 0))
            .join(Issue, Issue.id == Worklog.issue_id)
            .where(
                Issue.project_id == project_id,
            )
            .group_by(Worklog.user_id)
        )
    ).all()
    worklog_user_ids = {str(row[0]) for row in worklog_rows}

    missing_user_ids = (assignee_ids | worklog_user_ids) - set(participant_names.keys())
    if missing_user_ids:
        missing_users = (
            await session.execute(
                select(User.id, User.full_name).where(User.id.in_([UUID(user_id) for user_id in missing_user_ids]))
            )
        ).all()
        for user_id, full_name in missing_users:
            participant_names[str(user_id)] = full_name

    tasks_by_assignee_counters: dict[str, dict[str, int]] = defaultdict(
        lambda: {"completed": 0, "in_progress": 0, "not_started": 0, "total": 0}
    )
    planned_by_assignee: dict[str, float] = defaultdict(float)
    open_tasks_by_assignee: dict[str, int] = defaultdict(int)
    open_planned_by_assignee: dict[str, float] = defaultdict(float)
    status_distribution: dict[str, int] = {str(status.id): 0 for status in statuses}

    overdue_tasks: list[schemas.DashboardOverdueTask] = []
    overdue_by_assignee: dict[str, int] = defaultdict(int)

    summary_completed = 0
    summary_in_progress = 0
    summary_not_started = 0
    total_planned_hours = 0.0

    today = date.today()
    now_utc = datetime.now(timezone.utc)
    recent_datetime_from = now_utc - timedelta(days=recent_days)
    recent_date_from = recent_datetime_from.date()

    recent_created_tasks = 0
    recent_completed_tasks = 0

    for row in task_rows:
        assignee_key = str(row.assignee_id) if row.assignee_id is not None else UNASSIGNED_KEY
        status = status_by_id.get(row.status_id) if row.status_id is not None else None
        status_category = status.category if status is not None else schemas.StatusCategory.TODO.value

        if status_category == schemas.StatusCategory.DONE.value:
            bucket = "completed"
            summary_completed += 1
        elif status_category == schemas.StatusCategory.IN_PROGRESS.value:
            bucket = "in_progress"
            summary_in_progress += 1
        else:
            bucket = "not_started"
            summary_not_started += 1

        tasks_by_assignee_counters[assignee_key][bucket] += 1
        tasks_by_assignee_counters[assignee_key]["total"] += 1

        planned_hours = _to_float(row.planned_hours)
        planned_by_assignee[assignee_key] += planned_hours
        total_planned_hours += planned_hours

        if row.status_id is not None and str(row.status_id) in status_distribution:
            status_distribution[str(row.status_id)] += 1

        if status_category != schemas.StatusCategory.DONE.value:
            open_tasks_by_assignee[assignee_key] += 1
            open_planned_by_assignee[assignee_key] += planned_hours

            if row.due_date is not None and row.due_date < today:
                days_overdue = (today - row.due_date).days
                assignee_name = participant_names.get(assignee_key, UNASSIGNED_NAME)
                overdue_by_assignee[assignee_key] += 1
                overdue_tasks.append(
                    schemas.DashboardOverdueTask(
                        issue_id=row.id,
                        issue_key=row.key,
                        title=row.title,
                        assignee_id=UUID(assignee_key) if assignee_key != UNASSIGNED_KEY else None,
                        assignee_name=assignee_name,
                        due_date=row.due_date,
                        status_name=status.name if status is not None else None,
                        days_overdue=days_overdue,
                    )
                )

        if row.created_at is not None and row.created_at >= recent_datetime_from:
            recent_created_tasks += 1
        if row.resolved_at is not None and row.resolved_at >= recent_datetime_from:
            recent_completed_tasks += 1

    actual_by_assignee: dict[str, float] = defaultdict(float)
    total_actual_hours = 0.0
    for user_id, total_hours in worklog_rows:
        key = str(user_id)
        hours = _to_float(total_hours)
        actual_by_assignee[key] += hours
        total_actual_hours += hours

    recent_logged_hours = _to_float(
        (
            await session.execute(
                select(func.coalesce(func.sum(Worklog.hours), 0))
                .join(Issue, Issue.id == Worklog.issue_id)
                .where(
                    Issue.project_id == project_id,
                    Worklog.work_date >= recent_date_from,
                )
            )
        ).scalar_one()
    )

    all_assignee_keys = set(tasks_by_assignee_counters.keys()) | set(participant_names.keys())
    if UNASSIGNED_KEY in tasks_by_assignee_counters:
        all_assignee_keys.add(UNASSIGNED_KEY)

    def _assignee_name(assignee_key: str) -> str:
        if assignee_key == UNASSIGNED_KEY:
            return UNASSIGNED_NAME
        return participant_names.get(assignee_key, "Неизвестный пользователь")

    tasks_by_assignee = [
        schemas.DashboardTaskByAssignee(
            assignee_id=UUID(assignee_key) if assignee_key != UNASSIGNED_KEY else None,
            assignee_name=_assignee_name(assignee_key),
            completed=tasks_by_assignee_counters[assignee_key]["completed"],
            in_progress=tasks_by_assignee_counters[assignee_key]["in_progress"],
            not_started=tasks_by_assignee_counters[assignee_key]["not_started"],
            total=tasks_by_assignee_counters[assignee_key]["total"],
        )
        for assignee_key in sorted(all_assignee_keys, key=lambda key: _assignee_name(key).lower())
        if tasks_by_assignee_counters[assignee_key]["total"] > 0
    ]

    effort_assignee_keys = set(planned_by_assignee.keys()) | set(actual_by_assignee.keys()) | set(
        participant_names.keys()
    )
    effort_by_assignee = []
    for assignee_key in sorted(effort_assignee_keys, key=lambda key: _assignee_name(key).lower()):
        planned = round(planned_by_assignee[assignee_key], 2)
        actual = round(actual_by_assignee[assignee_key], 2)
        if planned == 0 and actual == 0:
            continue
        effort_by_assignee.append(
            schemas.DashboardEffortByAssignee(
                assignee_id=UUID(assignee_key) if assignee_key != UNASSIGNED_KEY else None,
                assignee_name=_assignee_name(assignee_key),
                planned_hours=planned,
                actual_hours=actual,
                variance_hours=_variance(actual, planned),
                actual_vs_plan_percent=_percent(actual, planned),
            )
        )

    overdue_tasks.sort(key=lambda item: item.days_overdue, reverse=True)
    total_overdue_tasks = len(overdue_tasks)
    overdue_tasks = overdue_tasks[:overdue_limit]
    overdue_assignee_items = [
        schemas.DashboardOverdueByAssignee(
            assignee_id=UUID(assignee_key) if assignee_key != UNASSIGNED_KEY else None,
            assignee_name=_assignee_name(assignee_key),
            tasks_count=tasks_count,
        )
        for assignee_key, tasks_count in sorted(
            overdue_by_assignee.items(),
            key=lambda item: (-item[1], _assignee_name(item[0]).lower()),
        )
    ]

    workload_assignee_keys = set(open_tasks_by_assignee.keys()) | set(participant_names.keys())
    workload = [
        schemas.DashboardWorkloadItem(
            assignee_id=UUID(assignee_key) if assignee_key != UNASSIGNED_KEY else None,
            assignee_name=_assignee_name(assignee_key),
            open_tasks=open_tasks_by_assignee[assignee_key],
            planned_hours_open_tasks=round(open_planned_by_assignee[assignee_key], 2),
        )
        for assignee_key in sorted(workload_assignee_keys, key=lambda key: _assignee_name(key).lower())
        if open_tasks_by_assignee[assignee_key] > 0
    ]

    status_distribution_items = [
        schemas.DashboardStatusDistributionItem(
            status_id=status.id,
            status_name=status.name,
            status_category=status.category,
            tasks_count=status_distribution.get(str(status.id), 0),
        )
        for status in statuses
    ]

    total_tasks = summary_completed + summary_in_progress + summary_not_started
    total_planned_hours = round(total_planned_hours, 2)
    total_actual_hours = round(total_actual_hours, 2)

    return schemas.ProjectDashboardReportResponse(
        project_id=project_id,
        generated_at=now_utc,
        task_summary=schemas.DashboardTaskSummary(
            completed=summary_completed,
            in_progress=summary_in_progress,
            not_started=summary_not_started,
            total=total_tasks,
        ),
        tasks_by_assignee=tasks_by_assignee,
        effort_summary=schemas.DashboardEffortSummary(
            planned_hours=total_planned_hours,
            actual_hours=total_actual_hours,
            variance_hours=_variance(total_actual_hours, total_planned_hours),
            actual_vs_plan_percent=_percent(total_actual_hours, total_planned_hours),
        ),
        effort_by_assignee=effort_by_assignee,
        status_distribution=status_distribution_items,
        overdue=schemas.DashboardOverdueSection(
            total_overdue_tasks=total_overdue_tasks,
            overdue_by_assignee=overdue_assignee_items,
            tasks=overdue_tasks,
        ),
        workload=workload,
        recent_activity=schemas.DashboardRecentActivity(
            days=recent_days,
            created_tasks=recent_created_tasks,
            completed_tasks=recent_completed_tasks,
            logged_hours=round(recent_logged_hours, 2),
            completion_to_creation_percent=_percent(
                float(recent_completed_tasks),
                float(recent_created_tasks),
            ),
        ),
    )


@router.get(
    "/projects/{project_id}/reports/dashboard",
    response_model=schemas.ProjectDashboardReportResponse,
)
async def get_project_dashboard_report(
    project_id: UUID,
    session: Session,
    current_user: CurrentUser,
    recent_days: int = Query(14, ge=1, le=365),
    overdue_limit: int = Query(20, ge=1, le=100),
):
    """JSON-отчет и дашборд по задачам/трудозатратам проекта."""
    return await _build_project_dashboard_report(
        project_id=project_id,
        session=session,
        current_user=current_user,
        recent_days=recent_days,
        overdue_limit=overdue_limit,
    )


@router.get("/projects/{project_id}/reports/dashboard/export")
async def export_project_dashboard_report(
    project_id: UUID,
    session: Session,
    current_user: CurrentUser,
    recent_days: int = Query(14, ge=1, le=365),
    overdue_limit: int = Query(20, ge=1, le=100),
    export_format: Literal["csv", "excel"] = Query("csv", alias="format"),
):
    """Выгрузка дашборда в файл CSV или Excel (табличный long-form)."""
    report = await _build_project_dashboard_report(
        project_id=project_id,
        session=session,
        current_user=current_user,
        recent_days=recent_days,
        overdue_limit=overdue_limit,
    )
    rows = _build_dashboard_export_rows(report)
    generated_part = report.generated_at.strftime("%Y%m%d-%H%M%S")

    if export_format == "excel":
        content = _build_dashboard_excel(rows)
        filename = f"project-dashboard-{generated_part}.xls"
        media_type = "application/vnd.ms-excel"
    else:
        content = _build_dashboard_csv(rows)
        filename = f"project-dashboard-{generated_part}.csv"
        media_type = "text/csv; charset=utf-8"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
