from __future__ import annotations

from datetime import date, datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DashboardTaskSummary(BaseModel):
    completed: int
    in_progress: int
    not_started: int
    total: int


class DashboardTaskByAssignee(BaseModel):
    assignee_id: UUID | None = None
    assignee_name: str
    completed: int
    in_progress: int
    not_started: int
    total: int


class DashboardEffortSummary(BaseModel):
    planned_hours: float
    actual_hours: float
    variance_hours: float
    actual_vs_plan_percent: float | None = None


class DashboardEffortByAssignee(BaseModel):
    assignee_id: UUID | None = None
    assignee_name: str
    planned_hours: float
    actual_hours: float
    variance_hours: float
    actual_vs_plan_percent: float | None = None


class DashboardStatusDistributionItem(BaseModel):
    status_id: UUID
    status_name: str
    status_category: str
    tasks_count: int


class DashboardOverdueTask(BaseModel):
    issue_id: UUID
    issue_key: str
    title: str
    assignee_id: UUID | None = None
    assignee_name: str
    due_date: date
    status_name: str | None = None
    days_overdue: int


class DashboardOverdueByAssignee(BaseModel):
    assignee_id: UUID | None = None
    assignee_name: str
    tasks_count: int


class DashboardOverdueSection(BaseModel):
    total_overdue_tasks: int
    overdue_by_assignee: List[DashboardOverdueByAssignee]
    tasks: List[DashboardOverdueTask]


class DashboardWorkloadItem(BaseModel):
    assignee_id: UUID | None = None
    assignee_name: str
    open_tasks: int
    planned_hours_open_tasks: float


class DashboardRecentActivity(BaseModel):
    days: int
    created_tasks: int
    completed_tasks: int
    logged_hours: float
    completion_to_creation_percent: float | None = None


class ProjectDashboardReportResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    project_id: UUID
    generated_at: datetime
    task_summary: DashboardTaskSummary
    tasks_by_assignee: List[DashboardTaskByAssignee]
    effort_summary: DashboardEffortSummary
    effort_by_assignee: List[DashboardEffortByAssignee]
    status_distribution: List[DashboardStatusDistributionItem]
    overdue: DashboardOverdueSection
    workload: List[DashboardWorkloadItem]
    recent_activity: DashboardRecentActivity
