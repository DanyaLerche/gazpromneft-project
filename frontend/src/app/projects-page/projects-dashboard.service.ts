import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { UserProfilePreferencesService } from '@trungk18/core/services/user-profile-preferences.service';
import { IssuePriority, IssueType, JIssue } from '@trungk18/interface/issue';
import { JProjectSummary } from '@trungk18/interface/project';
import { AppRole, ProjectRole } from '@trungk18/interface/role';
import { JStatus } from '@trungk18/interface/status';
import { JUser } from '@trungk18/interface/user';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { environment } from 'src/environments/environment';

interface ApiForMeResponse {
  issues: ApiIssue[];
  projects: ApiProject[];
  total: number;
  filters: {
    statuses: ApiStatus[];
    users: ApiUser[];
  };
  mini_digest: ApiMiniDigest;
  action_history: ApiActionHistory;
}

interface ApiIssue {
  id: string;
  project_id: string;
  key: string;
  type: string;
  title: string;
  description: string | null;
  status_id: string | null;
  criticality_id: string | null;
  author_id: string;
  assignee_id: string | null;
  parent_id: string | null;
  start_date: string | null;
  due_date: string | null;
  taken_in_work_at: string | null;
  resolved_at: string | null;
  planned_hours: number | null;
  logged_hours?: number | null;
  created_at: string;
  updated_at: string;
}

interface ApiProject {
  id: string;
  key: string;
  name: string;
  description: string;
  category: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  current_user_role: ProjectRole;
}

interface ApiStatus {
  id: string;
  project_id: string;
  name: string;
  category: JStatus['category'];
  sort_order: number;
}

interface ApiUser {
  id: string;
  email: string;
  full_name: string;
  avatar_url?: string | null;
  is_active: boolean;
  app_role: AppRole;
  created_at: string;
}

interface ApiPagedUsers {
  items: ApiUser[];
  total: number;
}

interface ApiMiniDigestItem {
  item_type: 'issue_updated' | 'new_comment';
  issue_id: string;
  issue_key: string;
  issue_title: string;
  project_id: string;
  occurred_at: string;
  summary: string;
}

interface ApiMiniDigest {
  last_seen_timestamp: string | null;
  generated_at: string;
  items: ApiMiniDigestItem[];
}

interface ApiActionHistoryItem {
  action_type: 'issue_created' | 'comment_added' | 'worklog_added';
  issue_id: string;
  issue_key: string;
  issue_title: string;
  project_id: string;
  occurred_at: string;
  summary: string;
}

interface ApiActionHistory {
  items: ApiActionHistoryItem[];
}

export interface DashboardDigestItem {
  itemType: 'issue_updated' | 'new_comment';
  issueId: string;
  issueKey: string;
  issueTitle: string;
  projectId: string;
  occurredAt: string;
  summary: string;
}

export interface DashboardActionHistoryItem {
  actionType: 'issue_created' | 'comment_added' | 'worklog_added';
  issueId: string;
  issueKey: string;
  issueTitle: string;
  projectId: string;
  occurredAt: string;
  summary: string;
}

export interface ProjectsDashboardData {
  issues: JIssue[];
  projects: JProjectSummary[];
  statuses: JStatus[];
  users: JUser[];
  total: number;
  digestItems: DashboardDigestItem[];
  actionHistoryItems: DashboardActionHistoryItem[];
  digestGeneratedAt: string | null;
}

export interface PlatformUsersData {
  items: JUser[];
  total: number;
}

@Injectable({
  providedIn: 'root'
})
export class ProjectsDashboardService {
  private readonly baseUrl = environment.apiUrl;
  private readonly lastSeenStorageKey = 'for-me:last-seen-timestamp';

  constructor(
    private _http: HttpClient,
    private _profilePreferences: UserProfilePreferencesService
  ) {}

  getDashboardData(limit = 100): Observable<ProjectsDashboardData> {
    const lastSeenTimestamp = this.getLastSeenTimestamp();
    let params = new HttpParams()
      .set('sort', 'updated_at')
      .set('limit', String(limit))
      .set('offset', '0');
    if (lastSeenTimestamp) {
      params = params.set('last_seen_timestamp', lastSeenTimestamp);
    }

    return this._http.get<ApiForMeResponse>(`${this.baseUrl}/for-me`, { params }).pipe(
      map((response) => {
        const statuses = response.filters.statuses
          .map((status) => this.mapStatus(status))
          .sort((left, right) => left.sortOrder - right.sortOrder);
        const statusById = new Map(statuses.map((status) => [status.id, status]));
        const users = response.filters.users.map((user) => this.mapUser(user));
        const projects = response.projects
          .map((project) => this.mapProject(project))
          .sort(
            (left, right) =>
              new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime()
          );

        return {
          issues: response.issues.map((issue) => this.mapIssue(issue, statusById)),
          projects,
          statuses,
          users,
          total: response.total,
          digestItems: (response.mini_digest?.items ?? []).map((item) => this.mapDigestItem(item)),
          actionHistoryItems: (response.action_history?.items ?? []).map((item) =>
            this.mapActionHistoryItem(item)
          ),
          digestGeneratedAt: response.mini_digest?.generated_at ?? null
        };
      })
    );
  }

  markDashboardSeen(timestamp?: string): void {
    const value = timestamp ?? new Date().toISOString();
    try {
      window?.localStorage?.setItem(this.lastSeenStorageKey, value);
    } catch {
      // ignore storage errors (private mode, denied quota, etc.)
    }
  }

  listPlatformUsers(
    query = '',
    appRole: AppRole | null = null,
    limit = 50
  ): Observable<PlatformUsersData> {
    let params = new HttpParams()
      .set('limit', String(limit))
      .set('offset', '0');
    const trimmedQuery = query.trim();
    if (trimmedQuery) {
      params = params.set('q', trimmedQuery);
    }
    if (appRole) {
      params = params.set('app_role', appRole);
    }

    return this._http.get<ApiPagedUsers>(`${this.baseUrl}/users`, { params }).pipe(
      map((response) => ({
        items: response.items.map((user) => this.mapUser(user)),
        total: response.total
      }))
    );
  }

  updateUserAppRole(userId: string, appRole: AppRole): Observable<JUser> {
    return this._http
      .patch<ApiUser>(`${this.baseUrl}/users/${userId}`, { app_role: appRole })
      .pipe(map((user) => this.mapUser(user)));
  }

  private mapProject(project: ApiProject): JProjectSummary {
    return {
      id: project.id,
      key: project.key,
      name: project.name,
      createdBy: project.created_by,
      createdAt: project.created_at,
      currentUserRole: project.current_user_role ?? null
    };
  }

  private mapStatus(status: ApiStatus): JStatus {
    return {
      id: status.id,
      projectId: status.project_id,
      name: status.name,
      category: status.category,
      sortOrder: status.sort_order
    };
  }

  private mapUser(user: ApiUser): JUser {
    return this._profilePreferences.hydrateUser({
      id: user.id,
      name: user.full_name,
      email: user.email,
      avatarUrl: user.avatar_url ?? '',
      isActive: user.is_active,
      appRole: user.app_role,
      createdAt: user.created_at,
      updatedAt: user.created_at,
      issueIds: []
    });
  }

  private mapIssue(issue: ApiIssue, statusById: Map<string, JStatus>): JIssue {
    const status = issue.status_id ? statusById.get(issue.status_id) : undefined;
    const loggedHours = issue.logged_hours ?? null;
    const timeRemaining =
      issue.planned_hours !== null && issue.planned_hours !== undefined
        ? issue.planned_hours - (loggedHours ?? 0)
        : null;

    return {
      id: issue.id,
      key: issue.key,
      title: issue.title,
      type: (issue.type as IssueType) ?? IssueType.TASK,
      status: status?.name ?? issue.status_id ?? 'Без статуса',
      statusId: issue.status_id ?? '',
      statusName: status?.name ?? 'Без статуса',
      statusCategory: status?.category,
      priority: IssuePriority.MEDIUM,
      criticalityId: issue.criticality_id,
      criticalityName: null,
      criticalityLevel: null,
      listPosition: 0,
      description: issue.description ?? '',
      estimate: issue.planned_hours,
      timeSpent: loggedHours,
      timeRemaining,
      createdAt: issue.created_at,
      updatedAt: issue.updated_at,
      reporterId: issue.author_id,
      authorId: issue.author_id,
      assigneeId: issue.assignee_id,
      userIds: issue.assignee_id ? [issue.assignee_id] : [],
      comments: [],
      projectId: issue.project_id,
      parentId: issue.parent_id,
      startDate: issue.start_date,
      dueDate: issue.due_date,
      takenInWorkAt: issue.taken_in_work_at,
      resolvedAt: issue.resolved_at
    };
  }

  private mapDigestItem(item: ApiMiniDigestItem): DashboardDigestItem {
    return {
      itemType: item.item_type,
      issueId: item.issue_id,
      issueKey: item.issue_key,
      issueTitle: item.issue_title,
      projectId: item.project_id,
      occurredAt: item.occurred_at,
      summary: item.summary
    };
  }

  private mapActionHistoryItem(item: ApiActionHistoryItem): DashboardActionHistoryItem {
    return {
      actionType: item.action_type,
      issueId: item.issue_id,
      issueKey: item.issue_key,
      issueTitle: item.issue_title,
      projectId: item.project_id,
      occurredAt: item.occurred_at,
      summary: item.summary
    };
  }

  private getLastSeenTimestamp(): string | null {
    try {
      return window?.localStorage?.getItem(this.lastSeenStorageKey);
    } catch {
      return null;
    }
  }
}
