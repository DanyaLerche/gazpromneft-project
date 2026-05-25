import { HttpClient, HttpParams, HttpResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import {
  JEffortByAssignee,
  JEffortSummary,
  JOverdueByAssignee,
  JOverdueSection,
  JOverdueTask,
  JProjectDashboardReport,
  JRecentActivity,
  JStatusDistributionItem,
  JTaskByAssignee,
  JTaskSummary,
  JWorkloadItem
} from '@trungk18/interface/project';
import { Observable, throwError } from 'rxjs';
import { map } from 'rxjs/operators';
import { environment } from 'src/environments/environment';
import { ProjectService } from './project.service';

interface ApiDashboardTaskSummary {
  completed: number;
  in_progress: number;
  not_started: number;
  total: number;
}

interface ApiDashboardTaskByAssignee {
  assignee_id: string | null;
  assignee_name: string;
  completed: number;
  in_progress: number;
  not_started: number;
  total: number;
}

interface ApiDashboardEffortSummary {
  planned_hours: number;
  actual_hours: number;
  variance_hours: number;
  actual_vs_plan_percent: number | null;
}

interface ApiDashboardEffortByAssignee {
  assignee_id: string | null;
  assignee_name: string;
  planned_hours: number;
  actual_hours: number;
  variance_hours: number;
  actual_vs_plan_percent: number | null;
}

interface ApiDashboardStatusDistributionItem {
  status_id: string;
  status_name: string;
  status_category: string;
  tasks_count: number;
}

interface ApiDashboardOverdueTask {
  issue_id: string;
  issue_key: string;
  title: string;
  assignee_id: string | null;
  assignee_name: string;
  due_date: string;
  status_name: string | null;
  days_overdue: number;
}

interface ApiDashboardOverdueByAssignee {
  assignee_id: string | null;
  assignee_name: string;
  tasks_count: number;
}

interface ApiDashboardOverdueSection {
  total_overdue_tasks: number;
  overdue_by_assignee: ApiDashboardOverdueByAssignee[];
  tasks: ApiDashboardOverdueTask[];
}

interface ApiDashboardWorkloadItem {
  assignee_id: string | null;
  assignee_name: string;
  open_tasks: number;
  planned_hours_open_tasks: number;
}

interface ApiDashboardRecentActivity {
  days: number;
  created_tasks: number;
  completed_tasks: number;
  logged_hours: number;
  completion_to_creation_percent: number | null;
}

interface ApiProjectReportDashboard {
  project_id: string;
  generated_at: string;
  task_summary: ApiDashboardTaskSummary;
  tasks_by_assignee: ApiDashboardTaskByAssignee[];
  effort_summary: ApiDashboardEffortSummary;
  effort_by_assignee: ApiDashboardEffortByAssignee[];
  status_distribution: ApiDashboardStatusDistributionItem[];
  overdue: ApiDashboardOverdueSection;
  workload: ApiDashboardWorkloadItem[];
  recent_activity: ApiDashboardRecentActivity;
}

@Injectable({
  providedIn: 'root'
})
export class ProjectReportsService {
  private baseUrl = environment.apiUrl;

  constructor(
    private _http: HttpClient,
    private _projectService: ProjectService
  ) {}

  getProjectDashboardReport(recentDays = 14, overdueLimit = 20): Observable<JProjectDashboardReport> {
    const projectId = this._projectService.currentProjectId;
    if (!projectId) {
      return throwError(new Error('Project is not selected'));
    }

    const params = new HttpParams()
      .set('recent_days', String(recentDays))
      .set('overdue_limit', String(overdueLimit));
    return this._http
      .get<ApiProjectReportDashboard>(`${this.baseUrl}/projects/${projectId}/reports/dashboard`, {
        params
      })
      .pipe(map((response) => this.mapProjectDashboardReport(response)));
  }

  exportProjectDashboardReport(
    format: 'csv' | 'excel',
    recentDays = 14,
    overdueLimit = 20
  ): Observable<HttpResponse<Blob>> {
    const projectId = this._projectService.currentProjectId;
    if (!projectId) {
      return throwError(new Error('Project is not selected'));
    }

    const params = new HttpParams()
      .set('recent_days', String(recentDays))
      .set('overdue_limit', String(overdueLimit))
      .set('format', format);

    return this._http.get(`${this.baseUrl}/projects/${projectId}/reports/dashboard/export`, {
      params,
      observe: 'response',
      responseType: 'blob'
    });
  }

  private mapProjectDashboardReport(apiReport: ApiProjectReportDashboard): JProjectDashboardReport {
    return {
      projectId: apiReport.project_id,
      generatedAt: apiReport.generated_at,
      taskSummary: this.mapTaskSummary(apiReport.task_summary),
      tasksByAssignee: apiReport.tasks_by_assignee.map((row) => this.mapTaskByAssignee(row)),
      effortSummary: this.mapEffortSummary(apiReport.effort_summary),
      effortByAssignee: apiReport.effort_by_assignee.map((row) => this.mapEffortByAssignee(row)),
      statusDistribution: apiReport.status_distribution.map((row) =>
        this.mapStatusDistributionItem(row)
      ),
      overdue: this.mapOverdueSection(apiReport.overdue),
      workload: apiReport.workload.map((row) => this.mapWorkloadItem(row)),
      recentActivity: this.mapRecentActivity(apiReport.recent_activity)
    };
  }

  private mapTaskSummary(summary: ApiDashboardTaskSummary): JTaskSummary {
    return {
      completed: summary.completed,
      inProgress: summary.in_progress,
      notStarted: summary.not_started,
      total: summary.total
    };
  }

  private mapTaskByAssignee(row: ApiDashboardTaskByAssignee): JTaskByAssignee {
    return {
      assigneeId: row.assignee_id,
      assigneeName: row.assignee_name,
      completed: row.completed,
      inProgress: row.in_progress,
      notStarted: row.not_started,
      total: row.total
    };
  }

  private mapEffortSummary(summary: ApiDashboardEffortSummary): JEffortSummary {
    return {
      plannedHours: summary.planned_hours,
      actualHours: summary.actual_hours,
      varianceHours: summary.variance_hours,
      actualVsPlanPercent: summary.actual_vs_plan_percent
    };
  }

  private mapEffortByAssignee(row: ApiDashboardEffortByAssignee): JEffortByAssignee {
    return {
      assigneeId: row.assignee_id,
      assigneeName: row.assignee_name,
      plannedHours: row.planned_hours,
      actualHours: row.actual_hours,
      varianceHours: row.variance_hours,
      actualVsPlanPercent: row.actual_vs_plan_percent
    };
  }

  private mapStatusDistributionItem(item: ApiDashboardStatusDistributionItem): JStatusDistributionItem {
    return {
      statusId: item.status_id,
      statusName: item.status_name,
      statusCategory: item.status_category,
      tasksCount: item.tasks_count
    };
  }

  private mapOverdueSection(section: ApiDashboardOverdueSection): JOverdueSection {
    return {
      totalOverdueTasks: section.total_overdue_tasks,
      overdueByAssignee: section.overdue_by_assignee.map((item) => this.mapOverdueByAssignee(item)),
      tasks: section.tasks.map((item) => this.mapOverdueTask(item))
    };
  }

  private mapOverdueByAssignee(item: ApiDashboardOverdueByAssignee): JOverdueByAssignee {
    return {
      assigneeId: item.assignee_id,
      assigneeName: item.assignee_name,
      tasksCount: item.tasks_count
    };
  }

  private mapOverdueTask(item: ApiDashboardOverdueTask): JOverdueTask {
    return {
      issueId: item.issue_id,
      issueKey: item.issue_key,
      title: item.title,
      assigneeId: item.assignee_id,
      assigneeName: item.assignee_name,
      dueDate: item.due_date,
      statusName: item.status_name,
      daysOverdue: item.days_overdue
    };
  }

  private mapWorkloadItem(item: ApiDashboardWorkloadItem): JWorkloadItem {
    return {
      assigneeId: item.assignee_id,
      assigneeName: item.assignee_name,
      openTasks: item.open_tasks,
      plannedHoursOpenTasks: item.planned_hours_open_tasks
    };
  }

  private mapRecentActivity(activity: ApiDashboardRecentActivity): JRecentActivity {
    return {
      days: activity.days,
      createdTasks: activity.created_tasks,
      completedTasks: activity.completed_tasks,
      loggedHours: activity.logged_hours,
      completionToCreationPercent: activity.completion_to_creation_percent
    };
  }
}
