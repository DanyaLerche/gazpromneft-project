import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { arrayRemove, arrayUpsert } from '@datorama/akita';
import { JIssueAttachment } from '@trungk18/interface/attachment';
import { JComment } from '@trungk18/interface/comment';
import { JCriticality } from '@trungk18/interface/criticality';
import { IssuePriority, IssueType, JIssue } from '@trungk18/interface/issue';
import {
  JOnboardingAssignee,
  JOnboardingRecommendations,
  JOnboardingIssueItem,
  JOnboardingPersonItem,
  JOnboardingReadItem
} from '@trungk18/interface/onboarding';
import { JProject, JProjectSummary, ProjectCategory } from '@trungk18/interface/project';
import { AppRole, ProjectRole } from '@trungk18/interface/role';
import { JStatus } from '@trungk18/interface/status';
import { JUser } from '@trungk18/interface/user';
import { getApiErrorMessage } from '@trungk18/core/utils/api-error';
import { UserProfilePreferencesService } from '@trungk18/core/services/user-profile-preferences.service';
import { AuthQuery } from '@trungk18/project/auth/auth.query';
import { createInitialFilterState, FilterState } from '@trungk18/project/state/filter/filter.store';
import { DateUtil } from '@trungk18/project/utils/date';
import { createInitialState, ProjectState, ProjectStore } from './project.store';
import { EMPTY, Observable, forkJoin, of, throwError } from 'rxjs';
import { catchError, finalize, map, switchMap, tap } from 'rxjs/operators';
import { environment } from 'src/environments/environment';
import { NzNotificationService } from 'ng-zorro-antd/notification';

interface ApiProject {
  id: string;
  key: string;
  name: string;
  description: string;
  category: ProjectCategory;
  created_by: string;
  created_at: string;
  updated_at: string;
  current_user_role: ProjectRole;
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

interface ApiProjectUser {
  user: ApiUser;
  role: ProjectRole;
}

interface ApiProjectOnboardingPreferences {
  new_employee_mode: boolean;
}

interface ApiOnboardingAssignee {
  user_id: string;
  full_name: string;
  email?: string | null;
}

interface ApiProjectOnboardingAssigneesResponse {
  assignees: ApiOnboardingAssignee[];
}

interface ApiStatus {
  id: string;
  project_id: string;
  name: string;
  category: JStatus['category'];
  sort_order: number;
}

interface ApiCriticality {
  id: string;
  name: string;
  level: number;
}

interface ApiIssue {
  id: string;
  project_id: string;
  key: string;
  type: string;
  title: string;
  description: string | null;
  status_id: string;
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

interface ApiIssueComment {
  id: string;
  issue_id: string;
  author_id: string;
  body: string;
  created_at: string;
  updated_at: string;
}

interface ApiIssueAttachment {
  id: string;
  issue_id: string;
  uploaded_by: string;
  file_name: string;
  mime_type: string | null;
  size_bytes: number;
  storage_key: string;
  created_at: string;
}

interface ApiPagedProjects {
  items: ApiProject[];
  total: number;
}

interface ApiPagedProjectUsers {
  items: ApiProjectUser[];
  total: number;
}

interface ApiPagedUsers {
  items: ApiUser[];
  total: number;
}

interface ApiPagedIssues {
  items: ApiIssue[];
  total: number;
}

interface ApiOnboardingReadItem {
  page_id: string;
  title: string;
  reason: string;
  score: number | null;
}

interface ApiOnboardingIssueItem {
  issue_id: string;
  title: string;
  reason: string;
  score: number | null;
}

interface ApiOnboardingPersonItem {
  user_id: string;
  full_name: string;
  email?: string | null;
  reason: string;
  score: number | null;
}

interface ApiOnboardingRecommendationsResponse {
  reads: ApiOnboardingReadItem[];
  issues_to_review: ApiOnboardingIssueItem[];
  key_people: ApiOnboardingPersonItem[];
  generated_at: string;
  cached: boolean;
}

interface ApiIssueDetailsResponse {
  issue: ApiIssue;
  comments: ApiIssueComment[];
  worklog_summary?: {
    planned_hours: number | null;
    logged_hours: number | null;
  };
}

interface PrepareAttachmentUpload {
  storage_key: string;
  upload_url: string;
  headers: Record<string, string>;
  fields: Record<string, string>;
  method: 'POST';
  expires_in: number;
}

interface PrepareAttachmentResponse {
  upload: PrepareAttachmentUpload;
}

interface AttachmentResponse {
  attachment: ApiIssueAttachment;
}

interface AttachmentListResponse {
  items: ApiIssueAttachment[];
}

interface AttachmentDownloadResponse {
  download_url: string;
}

interface CreateProjectRequest {
  key: string;
  name: string;
}

interface UpdateProjectRequest {
  name?: string;
  description?: string;
  category?: ProjectCategory;
}

interface AddProjectUserRequest {
  user_id: string;
  role: ProjectRole;
}

interface UpdateProjectUserRequest {
  role: ProjectRole;
}

interface CreateIssueRequest {
  type: string;
  title: string;
  description: string | null;
  status_id: string;
  criticality_id: string | null;
  assignee_id: string | null;
  parent_id: string | null;
  start_date: string | null;
  due_date: string | null;
}

interface UpdateIssueRequest {
  title?: string;
  description?: string | null;
  status_id?: string;
  criticality_id?: string | null;
  assignee_id?: string | null;
  parent_id?: string | null;
  start_date?: string | null;
  due_date?: string | null;
}

interface ProjectResponse {
  project: ApiProject;
}

interface StatusesResponse {
  items: ApiStatus[];
}

interface CriticalitiesResponse {
  items: ApiCriticality[];
}

interface IssueResponse {
  issue: ApiIssue;
}

interface ProjectOnboardingPreferencesResponse {
  preferences: ApiProjectOnboardingPreferences;
}

export interface CreateIssuePayload {
  type: IssueType;
  title: string;
  description: string;
  statusId: string;
  criticalityId: string | null;
  assigneeId: string | null;
  parentId: string | null;
  startDate: string | null;
  dueDate: string | null;
}

interface PrepareIssueAttachmentPayload {
  file_name: string;
  mime_type: string;
  size_bytes: number;
}

interface CreateIssueAttachmentPayload {
  storage_key: string;
  file_name: string;
  mime_type: string;
  size_bytes: number;
}

export interface CreateProjectPayload {
  key: string;
  name: string;
}

export interface UpdateProjectSettingsPayload {
  name: string;
  description: string;
  category?: ProjectCategory;
}

@Injectable({
  providedIn: 'root'
})
export class ProjectService {
  baseUrl: string;
  private currentProjectIdValue: string | null = null;

  constructor(
    private _http: HttpClient,
    private _store: ProjectStore,
    private _notification: NzNotificationService,
    private _profilePreferences: UserProfilePreferencesService,
    private _authQuery: AuthQuery
  ) {
    this.baseUrl = environment.apiUrl;
  }

  get currentProjectId(): string | null {
    return this.currentProjectIdValue;
  }

  loadProjectIfNeeded(projectId: string) {
    if (this.currentProjectIdValue === projectId && this._store.getValue().id === projectId) {
      return;
    }

    this.loadProject(projectId);
  }

  setLoading(isLoading: boolean) {
    this._store.setLoading(isLoading);
  }

  listProjects(): Observable<JProjectSummary[]> {
    const params = new HttpParams().set('limit', '100').set('offset', '0');
    return this._http
      .get<ApiPagedProjects>(`${this.baseUrl}/projects`, { params })
      .pipe(
        map((response) => response.items.map((project) => this.mapProjectSummary(project)))
      );
  }

  createProject(payload: CreateProjectPayload): Observable<JProjectSummary> {
    const body: CreateProjectRequest = {
      key: payload.key.trim().toUpperCase(),
      name: payload.name.trim()
    };
    return this._http
      .post<ProjectResponse>(`${this.baseUrl}/projects`, body)
      .pipe(map(({ project }) => this.mapProjectSummary(project)));
  }

  loadProject(projectId: string) {
    this.currentProjectIdValue = projectId;
    this._store.update(() => createInitialState() as ProjectState);
    this._store.setLoading(true);
    this._store.setError(null);

    forkJoin({
      project: this._http
        .get<ProjectResponse>(`${this.baseUrl}/projects/${projectId}`)
        .pipe(map(({ project }) => project)),
      users: this._http
        .get<ApiPagedProjectUsers>(`${this.baseUrl}/projects/${projectId}/users`, {
          params: new HttpParams().set('limit', '100').set('offset', '0')
        })
        .pipe(map((response) => response.items)),
      preferences: this._http
        .get<ProjectOnboardingPreferencesResponse>(`${this.baseUrl}/projects/${projectId}/me/preferences`)
        .pipe(map((response) => response.preferences)),
      assignees: this._http
        .get<ApiProjectOnboardingAssigneesResponse>(`${this.baseUrl}/projects/${projectId}/onboarding/assignees`)
        .pipe(map((response) => response.assignees)),
      statuses: this._http
        .get<StatusesResponse>(`${this.baseUrl}/projects/${projectId}/statuses`)
        .pipe(map((response) => response.items)),
      criticalities: this._http
        .get<CriticalitiesResponse>(`${this.baseUrl}/criticalities`)
        .pipe(map((response) => response.items))
    })
      .pipe(
        tap(({ project, users, preferences, assignees, statuses, criticalities }) => {
          const mappedUsers = this.sortProjectUsers(
            users.map((item) => this.mapUser(item.user, item.role))
          );
          const mappedStatuses = statuses
            .map((status) => this.mapStatus(status))
            .sort((a, b) => a.sortOrder - b.sortOrder);
          const mappedCriticalities = criticalities
            .map((criticality) => this.mapCriticality(criticality))
            .sort((a, b) => a.level - b.level);

          this._store.update((state) => ({
            ...state,
            ...this.mapProjectPatch(project),
            newEmployeeMode: preferences.new_employee_mode ?? false,
            onboardingAssigneeIds: assignees.map((item) => item.user_id),
            users: mappedUsers,
            statuses: mappedStatuses,
            criticalities: mappedCriticalities,
            issues: []
          }));
        }),
        finalize(() => {
          this._store.setLoading(false);
        }),
        catchError((error) => {
          this._store.setError(error);
          return EMPTY;
        })
      )
      .subscribe(() => {
        this.loadIssues();
      });
  }

  getProject() {
    if (this.currentProjectIdValue) {
      this.loadProject(this.currentProjectIdValue);
    }
  }

  updateProjectSettings(
    payload: UpdateProjectSettingsPayload
  ): Observable<JProject> {
    if (!this.currentProjectIdValue) {
      return throwError(new Error('Project is not selected'));
    }

    const body: UpdateProjectRequest = {
      name: payload.name.trim(),
      description: payload.description.trim()
    };
    if (payload.category) {
      body.category = payload.category;
    }

    return this._http
      .patch<ProjectResponse>(`${this.baseUrl}/projects/${this.currentProjectIdValue}`, body)
      .pipe(
        map(({ project }) => {
          this.patchProject(project);
          return this._store.getValue();
        })
      );
  }

  getOnboardingRecommendations(force = false): Observable<JOnboardingRecommendations> {
    if (!this.currentProjectIdValue) {
      return throwError(new Error('Project is not selected'));
    }

    let params = new HttpParams();
    if (force) {
      params = params.set('force', 'true');
    }

    return this._http
      .get<ApiOnboardingRecommendationsResponse>(
        `${this.baseUrl}/projects/${this.currentProjectIdValue}/onboarding/recommendations`,
        { params }
      )
      .pipe(map((response) => this.mapOnboardingRecommendations(response)));
  }

  updateOnboardingPreferences(newEmployeeMode: boolean): Observable<boolean> {
    if (!this.currentProjectIdValue) {
      return throwError(new Error('Project is not selected'));
    }

    return this._http
      .patch<ProjectOnboardingPreferencesResponse>(
        `${this.baseUrl}/projects/${this.currentProjectIdValue}/me/preferences`,
        { new_employee_mode: newEmployeeMode }
      )
      .pipe(
        map(({ preferences }) => {
          const nextValue = preferences.new_employee_mode ?? false;
          this._store.update((state) => ({
            ...state,
            newEmployeeMode: nextValue
          }));
          return nextValue;
        })
      );
  }

  getOnboardingAssignees(): Observable<JOnboardingAssignee[]> {
    if (!this.currentProjectIdValue) {
      return of([]);
    }

    return this._http
      .get<ApiProjectOnboardingAssigneesResponse>(
        `${this.baseUrl}/projects/${this.currentProjectIdValue}/onboarding/assignees`
      )
      .pipe(
        map((response) => response.assignees.map((item) => this.mapOnboardingAssigneeItem(item))),
        tap((assignees) => {
          this.syncOnboardingAssignmentState(assignees);
        })
      );
  }

  updateOnboardingAssignees(userIds: string[]): Observable<JOnboardingAssignee[]> {
    if (!this.currentProjectIdValue) {
      return throwError(new Error('Project is not selected'));
    }

    return this._http
      .patch<ApiProjectOnboardingAssigneesResponse>(
        `${this.baseUrl}/projects/${this.currentProjectIdValue}/onboarding/assignees`,
        { user_ids: userIds }
      )
      .pipe(
        map((response) => response.assignees.map((item) => this.mapOnboardingAssigneeItem(item))),
        tap((assignees) => {
          this.syncOnboardingAssignmentState(assignees);
        })
      );
  }

  searchAvailableProjectUsers(query = ''): Observable<JUser[]> {
    if (!this.currentProjectIdValue) {
      return of([]);
    }

    let params = new HttpParams().set('limit', '20').set('offset', '0');
    const trimmedQuery = query.trim();
    if (trimmedQuery) {
      params = params.set('q', trimmedQuery);
    }

    return this._http
      .get<ApiPagedUsers>(`${this.baseUrl}/projects/${this.currentProjectIdValue}/users/search`, {
        params
      })
      .pipe(map((response) => response.items.map((user) => this.mapUser(user))));
  }

  addProjectUser(user: JUser, role: ProjectRole): Observable<JUser> {
    if (!this.currentProjectIdValue) {
      return throwError(new Error('Project is not selected'));
    }

    const body: AddProjectUserRequest = {
      user_id: user.id,
      role
    };

    return this._http
      .post(`${this.baseUrl}/projects/${this.currentProjectIdValue}/users`, body)
      .pipe(
        map(() => {
          const nextUser: JUser = {
            ...user,
            projectRole: role
          };
          this.upsertProjectUser(nextUser);
          return nextUser;
        })
      );
  }

  updateProjectUserRole(userId: string, role: ProjectRole): Observable<JUser | undefined> {
    if (!this.currentProjectIdValue) {
      return throwError(new Error('Project is not selected'));
    }

    const body: UpdateProjectUserRequest = { role };
    return this._http
      .patch(`${this.baseUrl}/projects/${this.currentProjectIdValue}/users/${userId}`, body)
      .pipe(
        map(() => {
          const currentUser = this._store.getValue().users.find((user) => user.id === userId);
          if (!currentUser) {
            return undefined;
          }

          const nextUser: JUser = {
            ...currentUser,
            projectRole: role
          };
          this.upsertProjectUser(nextUser);
          return nextUser;
        })
      );
  }

  removeProjectUser(userId: string): Observable<void> {
    if (!this.currentProjectIdValue) {
      return throwError(new Error('Project is not selected'));
    }

    return this._http
      .delete<void>(`${this.baseUrl}/projects/${this.currentProjectIdValue}/users/${userId}`)
      .pipe(
        map(() => {
          this.deleteProjectUser(userId);
          return void 0;
        })
      );
  }

  loadIssues(filters?: Partial<FilterState>) {
    if (!this.currentProjectIdValue) {
      return;
    }

    const effectiveFilters: FilterState = {
      ...createInitialFilterState(),
      ...filters
    };
    let params = new HttpParams().set('limit', '200').set('offset', '0');

    if (effectiveFilters.q) {
      params = params.set('q', effectiveFilters.q);
    }
    if (effectiveFilters.statusId) {
      params = params.set('status_id', effectiveFilters.statusId);
    }
    if (effectiveFilters.assigneeId) {
      params = params.set('assignee_id', effectiveFilters.assigneeId);
    }

    this._store.setLoading(true);
    this._http
      .get<ApiPagedIssues>(`${this.baseUrl}/projects/${this.currentProjectIdValue}/issues`, { params })
      .pipe(
        map((response) => this.applyClientFilters(this.mapIssues(response.items), effectiveFilters)),
        tap((issues) => {
          this._store.update((state) => ({
            ...state,
            issues
          }));
        }),
        finalize(() => {
          this._store.setLoading(false);
        }),
        catchError((error) => {
          this._store.setError(error);
          return of(error);
        })
      )
      .subscribe();
  }

  loadIssue(issueId: string): Observable<JIssue> {
    return this._http
      .get<ApiIssueDetailsResponse>(`${this.baseUrl}/issues/${issueId}`)
      .pipe(
        map((response) => {
          const currentIssue = this._store.getValue().issues.find((issue) => issue.id === issueId);
          const mappedIssue = this.mapIssue(response.issue, {
            comments: response.comments.map((comment) => this.mapComment(comment)),
            listPosition: currentIssue?.listPosition,
            loggedHours: response.worklog_summary?.logged_hours ?? response.issue.logged_hours ?? null
          });
          this.upsertIssue(mappedIssue);
          return mappedIssue;
        }),
        catchError((error) => throwError(error))
      );
  }

  createIssue(payload: CreateIssuePayload): Observable<JIssue> {
    if (!this.currentProjectIdValue) {
      return throwError(new Error('Project is not selected'));
    }

    const requestBody: CreateIssueRequest = {
      type: payload.type,
      title: payload.title.trim(),
      description: this.normalizeIssueDescription(payload.description),
      status_id: payload.statusId,
      criticality_id: payload.criticalityId,
      assignee_id: payload.assigneeId,
      parent_id: payload.type === IssueType.TASK ? payload.parentId : null,
      start_date: this.normalizeIssueDate(payload.startDate),
      due_date: this.normalizeIssueDate(payload.dueDate)
    };

    return this._http
      .post<IssueResponse>(
        `${this.baseUrl}/projects/${this.currentProjectIdValue}/issues`,
        requestBody
      )
      .pipe(
        map(({ issue }) => {
          const mappedIssue = this.mapIssue(issue, {
            listPosition: this.getNextIssuePosition(issue.status_id)
          });
          this.upsertIssue(mappedIssue);
          return mappedIssue;
        })
      );
  }

  updateIssue(issuePatch: Partial<JIssue> & Pick<JIssue, 'id'>) {
    const existingIssue = this._store.getValue().issues.find((issue) => issue.id === issuePatch.id);
    if (!existingIssue) {
      return;
    }

    const mergedIssue: JIssue = {
      ...existingIssue,
      ...issuePatch,
      reporterId: issuePatch.reporterId ?? existingIssue.reporterId,
      authorId: issuePatch.authorId ?? existingIssue.authorId,
      assigneeId:
        issuePatch.assigneeId !== undefined ? issuePatch.assigneeId : existingIssue.assigneeId,
      userIds:
        issuePatch.userIds !== undefined
          ? issuePatch.userIds
          : issuePatch.assigneeId !== undefined
            ? issuePatch.assigneeId
              ? [issuePatch.assigneeId]
              : []
            : existingIssue.userIds
    };
    const nextIssue = this.enrichIssueCriticality(mergedIssue);

    const requestBody: UpdateIssueRequest = {};
    if (issuePatch.title !== undefined) {
      const nextTitle = nextIssue.title.trim();
      if (nextTitle && nextTitle !== existingIssue.title) {
        requestBody.title = nextTitle;
      }
    }
    if (issuePatch.description !== undefined) {
      const nextDescription = this.normalizeIssueDescription(nextIssue.description);
      const currentDescription = this.normalizeIssueDescription(existingIssue.description);
      if (nextDescription !== currentDescription) {
        requestBody.description = nextDescription;
      }
    }
    if (issuePatch.statusId !== undefined && nextIssue.statusId !== existingIssue.statusId) {
      requestBody.status_id = nextIssue.statusId;
    }
    if (issuePatch.assigneeId !== undefined || issuePatch.userIds !== undefined) {
      const nextAssigneeId = nextIssue.assigneeId ?? nextIssue.userIds[0] ?? null;
      const currentAssigneeId = existingIssue.assigneeId ?? existingIssue.userIds[0] ?? null;
      if (nextAssigneeId !== currentAssigneeId) {
        requestBody.assignee_id = nextAssigneeId;
      }
    }
    if (
      issuePatch.parentId !== undefined &&
      (nextIssue.parentId ?? null) !== (existingIssue.parentId ?? null)
    ) {
      requestBody.parent_id = nextIssue.parentId ?? null;
    }
    if (
      issuePatch.criticalityId !== undefined &&
      (nextIssue.criticalityId ?? null) !== (existingIssue.criticalityId ?? null)
    ) {
      requestBody.criticality_id = nextIssue.criticalityId ?? null;
    }
    if (issuePatch.startDate !== undefined) {
      const nextStartDate = this.normalizeIssueDate(nextIssue.startDate);
      const currentStartDate = this.normalizeIssueDate(existingIssue.startDate);
      if (nextStartDate !== currentStartDate) {
        requestBody.start_date = nextStartDate;
      }
    }
    if (issuePatch.dueDate !== undefined) {
      const nextDueDate = this.normalizeIssueDate(nextIssue.dueDate);
      const currentDueDate = this.normalizeIssueDate(existingIssue.dueDate);
      if (nextDueDate !== currentDueDate) {
        requestBody.due_date = nextDueDate;
      }
    }

    if (!Object.keys(requestBody).length) {
      return;
    }

    this.upsertIssue({
      ...nextIssue,
      updatedAt: new Date().toISOString()
    });

    this._http
      .patch<IssueResponse>(`${this.baseUrl}/issues/${nextIssue.id}`, requestBody)
      .pipe(
        map(({ issue }) =>
          this.mapIssue(issue, {
            comments: existingIssue.comments,
            listPosition: nextIssue.listPosition,
            loggedHours: existingIssue.timeSpent
          })
        ),
        tap((issue) => {
          this.upsertIssue(issue);
        }),
        catchError((error) => {
          this._store.setError(error);
          this.upsertIssue(existingIssue);
          this._notification.error(
            error?.status === 403
              ? 'Нет доступа к задаче'
              : error?.status === 404
                ? 'Задача не найдена'
                : 'Не удалось сохранить изменения',
            getApiErrorMessage(error, 'Обновление задачи завершилось ошибкой.')
          );
          return EMPTY;
        })
      )
      .subscribe();
  }

  deleteIssue(issueId: string): Observable<void> {
    return this._http
      .delete<void>(`${this.baseUrl}/issues/${issueId}`)
      .pipe(
        map(() => {
          this._store.update((state) => ({
            ...state,
            issues: state.issues
              .filter((issue) => issue.id !== issueId)
              .map((issue) =>
                issue.parentId === issueId
                  ? {
                      ...issue,
                      parentId: null
                    }
                  : issue
              )
          }));
          return void 0;
        })
      );
  }

  deleteProject(projectId = this.currentProjectIdValue): Observable<void> {
    if (!projectId) {
      return throwError(new Error('Project is not selected'));
    }

    return this._http
      .delete<void>(`${this.baseUrl}/projects/${projectId}`)
      .pipe(
        map(() => {
          if (this.currentProjectIdValue === projectId) {
            this.currentProjectIdValue = null;
            this._store.update(() => createInitialState());
          }
          return void 0;
        })
      );
  }

  listIssueAttachments(issueId: string): Observable<JIssueAttachment[]> {
    return this._http
      .get<AttachmentListResponse>(`${this.baseUrl}/issues/${issueId}/attachments`)
      .pipe(map((response) => response.items.map((item) => this.mapIssueAttachment(item))));
  }

  prepareIssueAttachmentUpload(issueId: string, file: File): Observable<PrepareAttachmentUpload> {
    const body: PrepareIssueAttachmentPayload = {
      file_name: file.name,
      mime_type: file.type || 'application/octet-stream',
      size_bytes: file.size
    };

    return this._http
      .post<PrepareAttachmentResponse>(`${this.baseUrl}/issues/${issueId}/attachments/prepare`, body)
      .pipe(map((response) => response.upload));
  }

  uploadIssueAttachmentToStorage(upload: PrepareAttachmentUpload, file: File): Observable<void> {
    if (upload.method !== 'POST') {
      return throwError(new Error(`Unsupported upload method: ${upload.method}`));
    }

    const formData = new FormData();
    Object.entries(upload.fields ?? {}).forEach(([key, value]) => {
      formData.append(key, value);
    });
    formData.append('file', file, file.name);

    const headers = new HttpHeaders(upload.headers ?? {});
    return this._http.post(upload.upload_url, formData, { headers }).pipe(map(() => void 0));
  }

  createIssueAttachment(
    issueId: string,
    payload: CreateIssueAttachmentPayload
  ): Observable<JIssueAttachment> {
    return this._http
      .post<AttachmentResponse>(`${this.baseUrl}/issues/${issueId}/attachments`, payload)
      .pipe(map((response) => this.mapIssueAttachment(response.attachment)));
  }

  uploadIssueAttachment(issueId: string, file: File): Observable<JIssueAttachment> {
    const mimeType = file.type || 'application/octet-stream';

    return this.prepareIssueAttachmentUpload(issueId, file).pipe(
      switchMap((upload) =>
        this.uploadIssueAttachmentToStorage(upload, file).pipe(
          switchMap(() =>
            this.createIssueAttachment(issueId, {
              storage_key: upload.storage_key,
              file_name: file.name,
              mime_type: mimeType,
              size_bytes: file.size
            })
          )
        )
      )
    );
  }

  getIssueAttachmentDownloadUrl(attachmentId: string): Observable<string> {
    return this._http
      .get<AttachmentDownloadResponse>(`${this.baseUrl}/attachments/${attachmentId}/download`)
      .pipe(map((response) => response.download_url));
  }

  deleteIssueAttachment(attachmentId: string): Observable<void> {
    return this._http
      .delete<void>(`${this.baseUrl}/attachments/${attachmentId}`)
      .pipe(map(() => void 0));
  }

  updateIssueComment(issueId: string, comment: JComment) {
    const allIssues = this._store.getValue().issues;
    const issue = allIssues.find((x) => x.id === issueId);
    if (!issue) {
      return;
    }

    const comments = arrayUpsert(issue.comments ?? [], comment.id, comment);
    this.updateIssue({
      ...issue,
      comments
    });
  }

  private getNextIssuePosition(statusId: string): number {
    return this._store.getValue().issues.filter((issue) => issue.statusId === statusId).length + 1;
  }

  private normalizeIssueDescription(value: string | null | undefined): string | null {
    const trimmedValue = value?.trim() ?? '';
    if (!trimmedValue) {
      return null;
    }

    const normalizedValue = trimmedValue
      .replace(/<(p|div)><br><\/(p|div)>/g, '')
      .replace(/<(p|div)>\s*<\/(p|div)>/g, '')
      .replace(/&nbsp;/g, '')
      .replace(/\s/g, '');

    return normalizedValue ? trimmedValue : null;
  }

  private normalizeIssueDate(value: string | Date | null | undefined): string | null {
    return DateUtil.formatDateOnly(value);
  }

  private applyClientFilters(issues: JIssue[], filters: FilterState): JIssue[] {
    return issues.filter((issue) => {
      if (filters.criticalityIds.length && !filters.criticalityIds.includes(issue.criticalityId ?? '')) {
        return false;
      }
      if (filters.issueType && issue.type !== filters.issueType) {
        return false;
      }

      return true;
    });
  }

  private upsertIssue(issue: JIssue) {
    this._store.update((state) => {
      const issues = arrayUpsert(state.issues, issue.id, issue);
      return {
        ...state,
        issues
      };
    });
  }

  private patchProject(project: ApiProject) {
    this._store.update((state) => ({
      ...state,
      ...this.mapProjectPatch(project)
    }));
  }

  private upsertProjectUser(user: JUser) {
    const currentUserId = this._authQuery.getValue().user?.id ?? null;
    this._store.update((state) => ({
      ...state,
      users: this.sortProjectUsers(arrayUpsert(state.users, user.id, user)),
      currentUserRole:
        user.id === currentUserId ? user.projectRole ?? state.currentUserRole : state.currentUserRole
    }));
  }

  private deleteProjectUser(userId: string) {
    const currentUserId = this._authQuery.getValue().user?.id ?? null;
    this._store.update((state) => ({
      ...state,
      users: this.sortProjectUsers(arrayRemove(state.users, userId)),
      currentUserRole: userId === currentUserId ? null : state.currentUserRole
    }));
  }

  private mapProjectPatch(
    project: ApiProject
  ): Pick<
    JProject,
    'id' | 'key' | 'name' | 'createdBy' | 'createdAt' | 'description' | 'category' | 'updateAt' | 'currentUserRole'
  > {
    return {
      id: project.id,
      key: project.key,
      name: project.name,
      createdBy: project.created_by,
      createdAt: project.created_at,
      description: project.description ?? '',
      category: project.category ?? ProjectCategory.SOFTWARE,
      updateAt: project.updated_at ?? project.created_at,
      currentUserRole: project.current_user_role ?? null
    };
  }

  private mapOnboardingRecommendations(
    response: ApiOnboardingRecommendationsResponse
  ): JOnboardingRecommendations {
    return {
      reads: response.reads.map((item) => this.mapOnboardingReadItem(item)),
      issuesToReview: response.issues_to_review.map((item) => this.mapOnboardingIssueItem(item)),
      keyPeople: response.key_people.map((item) => this.mapOnboardingPersonItem(item)),
      generatedAt: response.generated_at,
      cached: response.cached
    };
  }

  private mapProjectSummary(project: ApiProject): JProjectSummary {
    return {
      id: project.id,
      key: project.key,
      name: project.name,
      createdBy: project.created_by,
      createdAt: project.created_at,
      currentUserRole: project.current_user_role ?? null
    };
  }

  private mapUser(user: ApiUser, projectRole?: ProjectRole): JUser {
    return this._profilePreferences.hydrateUser({
      id: user.id,
      name: user.full_name,
      email: user.email,
      avatarUrl: user.avatar_url ?? '',
      isActive: user.is_active,
      appRole: user.app_role,
      createdAt: user.created_at,
      updatedAt: user.created_at,
      issueIds: [],
      projectRole
    });
  }

  private sortProjectUsers(users: JUser[]): JUser[] {
    return users.slice().sort((left, right) => {
      const roleDiff =
        this.getProjectRoleWeight(right.projectRole) - this.getProjectRoleWeight(left.projectRole);
      if (roleDiff !== 0) {
        return roleDiff;
      }

      const leftLabel = (left.name || left.email || '').toLowerCase();
      const rightLabel = (right.name || right.email || '').toLowerCase();
      return leftLabel.localeCompare(rightLabel);
    });
  }

  private getProjectRoleWeight(role?: ProjectRole | null): number {
    return role === ProjectRole.ADMIN_PROJECT ? 1 : 0;
  }

  private mapOnboardingReadItem(item: ApiOnboardingReadItem): JOnboardingReadItem {
    return {
      pageId: item.page_id,
      title: item.title,
      reason: item.reason,
      score: item.score ?? null
    };
  }

  private mapOnboardingIssueItem(item: ApiOnboardingIssueItem): JOnboardingIssueItem {
    return {
      issueId: item.issue_id,
      title: item.title,
      reason: item.reason,
      score: item.score ?? null
    };
  }

  private mapOnboardingPersonItem(item: ApiOnboardingPersonItem): JOnboardingPersonItem {
    return {
      userId: item.user_id,
      fullName: item.full_name,
      email: item.email ?? null,
      reason: item.reason,
      score: item.score ?? null
    };
  }

  private mapOnboardingAssigneeItem(item: ApiOnboardingAssignee): JOnboardingAssignee {
    return {
      userId: item.user_id,
      fullName: item.full_name,
      email: item.email ?? null
    };
  }

  private syncOnboardingAssignmentState(assignees: JOnboardingAssignee[]): void {
    const assigneeIds = assignees.map((item) => item.userId);
    const currentUserId = this._authQuery.getValue().user?.id ?? null;
    this._store.update((state) => ({
      ...state,
      onboardingAssigneeIds: assigneeIds,
      newEmployeeMode: currentUserId ? assigneeIds.includes(currentUserId) : state.newEmployeeMode
    }));
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

  private mapCriticality(criticality: ApiCriticality): JCriticality {
    return {
      id: criticality.id,
      name: criticality.name,
      level: criticality.level
    };
  }

  private mapIssues(issues: ApiIssue[]): JIssue[] {
    const positions = new Map<string, number>();
    return issues.map((issue) => {
      const currentPosition = (positions.get(issue.status_id) ?? 0) + 1;
      positions.set(issue.status_id, currentPosition);
      return this.mapIssue(issue, { listPosition: currentPosition });
    });
  }

  private mapIssue(
    issue: ApiIssue,
    options: { comments?: JComment[]; listPosition?: number; loggedHours?: number | null } = {}
  ): JIssue {
    const status = this._store.getValue().statuses.find((item) => item.id === issue.status_id);
    const criticality = this._store
      .getValue()
      .criticalities.find((item) => item.id === issue.criticality_id);
    const loggedHours = options.loggedHours ?? issue.logged_hours ?? null;
    const timeRemaining =
      issue.planned_hours !== null && issue.planned_hours !== undefined
        ? issue.planned_hours - (loggedHours ?? 0)
        : null;

    return {
      id: issue.id,
      key: issue.key,
      title: issue.title,
      type: (issue.type as IssueType) ?? IssueType.TASK,
      status: status?.name ?? issue.status_id,
      statusId: issue.status_id,
      statusName: status?.name,
      statusCategory: status?.category,
      priority: this.mapCriticalityToPriority(criticality),
      criticalityId: issue.criticality_id,
      criticalityName: criticality?.name ?? null,
      criticalityLevel: criticality?.level ?? null,
      listPosition: options.listPosition ?? 0,
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
      comments: options.comments ?? [],
      projectId: issue.project_id,
      parentId: issue.parent_id,
      startDate: issue.start_date,
      dueDate: issue.due_date,
      takenInWorkAt: issue.taken_in_work_at,
      resolvedAt: issue.resolved_at
    };
  }

  private enrichIssueCriticality(issue: JIssue): JIssue {
    const criticality = this._store
      .getValue()
      .criticalities.find((item) => item.id === issue.criticalityId);

    return {
      ...issue,
      priority: criticality ? this.mapCriticalityToPriority(criticality) : issue.priority,
      criticalityName: criticality?.name ?? null,
      criticalityLevel: criticality?.level ?? null
    };
  }

  private mapCriticalityToPriority(criticality?: JCriticality | null): IssuePriority {
    if (!criticality) {
      return IssuePriority.MEDIUM;
    }

    if (criticality.level <= 1) {
      return IssuePriority.LOWEST;
    }
    if (criticality.level === 2) {
      return IssuePriority.LOW;
    }
    if (criticality.level === 3) {
      return IssuePriority.MEDIUM;
    }
    if (criticality.level === 4) {
      return IssuePriority.HIGH;
    }

    return IssuePriority.HIGHEST;
  }

  private mapComment(comment: ApiIssueComment): JComment {
    const user =
      this._store.getValue().users.find((item) => item.id === comment.author_id) ??
      ({
        id: comment.author_id,
        name: 'Unknown user',
        email: '',
        avatarUrl: ''
      } as JUser);

    return {
      id: comment.id,
      body: comment.body,
      createdAt: comment.created_at,
      updatedAt: comment.updated_at,
      issueId: comment.issue_id,
      userId: comment.author_id,
      user
    };
  }

  private mapIssueAttachment(attachment: ApiIssueAttachment): JIssueAttachment {
    return {
      id: attachment.id,
      issueId: attachment.issue_id,
      uploadedBy: attachment.uploaded_by,
      fileName: attachment.file_name,
      mimeType: attachment.mime_type,
      sizeBytes: attachment.size_bytes,
      storageKey: attachment.storage_key,
      createdAt: attachment.created_at
    };
  }
}
