import { Component, OnInit } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { getApiErrorMessage } from '@trungk18/core/utils/api-error';
import { NoWhitespaceValidator } from '@trungk18/core/validators/no-whitespace.validator';
import { IssueType, JIssue } from '@trungk18/interface/issue';
import { JProjectSummary } from '@trungk18/interface/project';
import {
  AppRole,
  getAppRoleLabel,
  getProjectRoleLabel,
  isAdminAppRole
} from '@trungk18/interface/role';
import { JStatus } from '@trungk18/interface/status';
import { JUser } from '@trungk18/interface/user';
import { AuthQuery } from '@trungk18/project/auth/auth.query';
import { AuthService } from '@trungk18/project/auth/auth.service';
import {
  CreateProjectPayload,
  ProjectService
} from '@trungk18/project/state/project/project.service';
import { finalize } from 'rxjs/operators';
import {
  DashboardActionHistoryItem,
  DashboardDigestItem,
  ProjectsDashboardData,
  ProjectsDashboardService
} from './projects-dashboard.service';
import { NzNotificationService } from 'ng-zorro-antd/notification';
import { FocusModeService } from '@trungk18/core/services/focus-mode.service';

interface DashboardStat {
  label: string;
  value: number;
  description: string;
  tone: 'primary' | 'danger' | 'warning' | 'info';
  icon: string;
}

@Component({
  selector: 'projects-page',
  templateUrl: './projects-page.component.html',
  styleUrls: ['./projects-page.component.scss']
})
export class ProjectsPageComponent implements OnInit {
  readonly loadingCards = Array.from({ length: 4 }, (_, index) => index);
  readonly profileRole = 'Участник платформы';
  readonly profileTeam = 'Платформа проектов';
  readonly profileInfo =
    'Работает с задачами, домашней панелью и быстрым доступом к проектам.';
  readonly introductionItems = [
    'Просматривайте задачи, которые назначены вам прямо сейчас.',
    'Следите за сроками и сразу переходите в нужный проект.',
    'Используйте домашнюю страницу как стартовую точку рабочего дня.'
  ];
  readonly platformRoleOptions = [AppRole.USER, AppRole.ADMIN_APP];

  projects: JProjectSummary[] = [];
  issues: JIssue[] = [];
  statuses: JStatus[] = [];
  users: JUser[] = [];
  platformUsers: JUser[] = [];
  isLoading = false;
  isLoadingPlatformUsers = false;
  isCreating = false;
  isLoggingOut = false;
  showCreateForm = false;
  errorMessage = '';
  createErrorMessage = '';
  platformUsersErrorMessage = '';
  searchQuery = '';
  platformUserSearchQuery = '';
  selectedStatusId = 'all';
  selectedAssignedFilter: 'all' | 'overdue' | 'today' | 'week' = 'all';
  selectedProjectId = 'all';
  selectedPlatformRoleFilter: 'all' | AppRole = 'all';
  digestItems: DashboardDigestItem[] = [];
  actionHistoryItems: DashboardActionHistoryItem[] = [];
  digestGeneratedAt: string | null = null;
  isFocusWidgetCollapsed = false;

  private readonly updatingPlatformUserIds = new Set<string>();
  private platformUsersSearchTimer: ReturnType<typeof setTimeout> | null = null;
  private readonly focusWidgetStorageKey = 'projects.focus-widget.collapsed';

  createForm = this._fb.group({
    name: [
      '',
      [Validators.required, NoWhitespaceValidator(), Validators.maxLength(200)]
    ],
    key: [
      '',
      [
        Validators.required,
        Validators.minLength(2),
        Validators.maxLength(20),
        Validators.pattern(/^[A-Za-z0-9_-]+$/),
        NoWhitespaceValidator()
      ]
    ]
  });

  constructor(
    private _dashboardService: ProjectsDashboardService,
    private _projectService: ProjectService,
    private _fb: FormBuilder,
    private _authService: AuthService,
    private _notification: NzNotificationService,
    public authQuery: AuthQuery,
    public focusMode: FocusModeService
  ) {}

  ngOnInit(): void {
    this.restoreFocusWidgetState();
    this.loadDashboard();
  }

  get currentProfileRole(): string {
    return getAppRoleLabel(this.authQuery.getValue().user?.appRole);
  }

  get canCreateProjects(): boolean {
    return Boolean(this.authQuery.getValue().user?.id);
  }

  get canManagePlatformUsers(): boolean {
    return isAdminAppRole(this.authQuery.getValue().user?.appRole);
  }

  get dashboardStats(): DashboardStat[] {
    const assignedIssues = this.assignedIssues;

    return [
      {
        label: 'Назначено мне',
        value: assignedIssues.length,
        description: 'Все активные задачи, назначенные текущему пользователю.',
        tone: 'primary',
        icon: 'board'
      },
      {
        label: 'Просрочено',
        value: this.overdueCount,
        description: 'Требуют внимания.',
        tone: 'danger',
        icon: 'filters'
      },
      {
        label: 'Срок сегодня',
        value: this.dueTodayCount,
        description: 'Задачи, которые лучше закрыть до конца дня.',
        tone: 'warning',
        icon: 'star'
      },
      {
        label: 'Обновлено за 7 дней',
        value: this.updatedThisWeek,
        description: 'Активность за неделю.',
        tone: 'info',
        icon: 'report'
      }
    ];
  }

  get overdueCount(): number {
    return this.assignedIssues.filter((issue) => this.isOverdue(issue)).length;
  }

  get dueTodayCount(): number {
    return this.assignedIssues.filter((issue) => this.isDueToday(issue)).length;
  }

  get updatedThisWeek(): number {
    return this.issues.filter((issue) => this.isUpdatedRecently(issue)).length;
  }

  get focusIssuesCount(): number {
    return this.assignedIssues.filter(
      (issue) => this.isOverdue(issue) || this.isDueToday(issue)
    ).length;
  }

  get activeProjectsCount(): number {
    return this.projects.length;
  }

  get latestActionHistoryItem(): DashboardActionHistoryItem | null {
    return this.actionHistoryItems[0] ?? null;
  }

  get assignedIssues(): JIssue[] {
    const currentUserId = this.authQuery.getValue().user?.id;
    if (!currentUserId) {
      return [];
    }

    return this.issues.filter((issue) => issue.assigneeId === currentUserId);
  }

  get filteredAssignedIssues(): JIssue[] {
    return this.assignedIssues.filter((issue) => {
      if (!this.matchesSearch(issue.key, issue.title, this.getProjectName(issue.projectId))) {
        return false;
      }

      if (this.selectedAssignedFilter === 'overdue' && !this.isOverdue(issue)) {
        return false;
      }

      if (this.selectedAssignedFilter === 'today' && !this.isDueToday(issue)) {
        return false;
      }

      if (this.selectedAssignedFilter === 'week' && !this.isDueThisWeek(issue)) {
        return false;
      }

      if (this.selectedProjectId !== 'all' && issue.projectId !== this.selectedProjectId) {
        return false;
      }

      return true;
    });
  }

  get visibleProjects(): JProjectSummary[] {
    return this.projects.filter((project) =>
      this.matchesSearch(project.key, project.name)
    );
  }

  get assignedProjects(): JProjectSummary[] {
    const projectIds = new Set(this.assignedIssues.map((issue) => issue.projectId).filter(Boolean));
    return this.projects.filter((project) => projectIds.has(project.id));
  }

  get activityIssues(): JIssue[] {
    return this.issues
      .filter((issue) =>
        this.matchesSearch(issue.key, issue.title, this.getProjectName(issue.projectId))
      )
      .slice()
      .sort(
        (left, right) =>
          new Date(this.getIssueActivityDate(right)).getTime() -
          new Date(this.getIssueActivityDate(left)).getTime()
      )
      .slice(0, 8);
  }

  openCreateForm() {
    if (!this.canCreateProjects) {
      return;
    }

    this.showCreateForm = true;
    this.createErrorMessage = '';
  }

  closeCreateForm() {
    this.showCreateForm = false;
    this.createErrorMessage = '';
    this.createForm.reset({ name: '', key: '' });
  }

  retryLoadDashboard() {
    this.loadDashboard();
  }

  onKeyInput() {
    const control = this.createForm.get('key');
    const rawValue = String(control?.value ?? '');
    const normalizedValue = rawValue.toUpperCase().replace(/\s+/g, '');

    if (normalizedValue !== rawValue) {
      control?.setValue(normalizedValue, { emitEvent: false });
    }
  }

  onSearchInput(event: Event) {
    this.searchQuery = String((event.target as HTMLInputElement)?.value ?? '');
  }

  onPlatformUserSearchInput(event: Event) {
    this.platformUserSearchQuery = String((event.target as HTMLInputElement)?.value ?? '');

    if (this.platformUsersSearchTimer) {
      clearTimeout(this.platformUsersSearchTimer);
    }
    this.platformUsersSearchTimer = setTimeout(() => {
      this.loadPlatformUsers();
    }, 250);
  }

  onPlatformRoleFilterChange(event: Event) {
    const value = String((event.target as HTMLSelectElement)?.value ?? 'all');
    this.selectedPlatformRoleFilter = value === 'all' ? 'all' : (value as AppRole);
    this.loadPlatformUsers();
  }

  selectAssignedFilter(filter: 'all' | 'overdue' | 'today' | 'week') {
    this.selectedAssignedFilter = filter;
  }

  clearAssignedFilters() {
    this.selectedAssignedFilter = 'all';
    this.selectedProjectId = 'all';
  }

  onAssignedProjectChange(event: Event) {
    this.selectedProjectId = String((event.target as HTMLSelectElement)?.value ?? 'all');
  }

  toggleFocusWidgetCollapsed() {
    this.isFocusWidgetCollapsed = !this.isFocusWidgetCollapsed;
    localStorage.setItem(this.focusWidgetStorageKey, JSON.stringify(this.isFocusWidgetCollapsed));
  }

  submitCreate() {
    if (!this.canCreateProjects) {
      this.createErrorMessage = 'У вас нет прав на создание проектов.';
      return;
    }

    if (this.createForm.invalid) {
      this.createForm.markAllAsTouched();
      return;
    }

    this.isCreating = true;
    this.createErrorMessage = '';
    const payload = this.createForm.getRawValue() as CreateProjectPayload;

    this._projectService
      .createProject(payload)
      .pipe(
        finalize(() => {
          this.isCreating = false;
        })
      )
      .subscribe({
        next: () => {
          this.closeCreateForm();
          this.loadDashboard();
        },
        error: (error) => {
          this.createErrorMessage = this.formatCreateError(error);
        }
      });
  }

  trackByProjectId(_index: number, project: JProjectSummary) {
    return project.id;
  }

  trackByIssueId(_index: number, issue: JIssue) {
    return issue.id;
  }

  trackByDigestItem(_index: number, item: DashboardDigestItem) {
    return `${item.itemType}-${item.issueId}-${item.occurredAt}`;
  }

  trackByActionHistoryItem(_index: number, item: DashboardActionHistoryItem) {
    return `${item.actionType}-${item.issueId}-${item.occurredAt}`;
  }

  trackByUserId(_index: number, user: JUser) {
    return user.id;
  }

  logout() {
    this.isLoggingOut = true;
    this._authService
      .logout()
      .pipe(
        finalize(() => {
          this.isLoggingOut = false;
        })
      )
      .subscribe();
  }

  getUserInitial(user: JUser | null): string {
    if (!user) {
      return '?';
    }

    return (user.name || user.email || '?').charAt(0).toUpperCase();
  }

  isCurrentUser(user: JUser): boolean {
    return this.authQuery.getValue().user?.id === user.id;
  }

  isPlatformUserUpdating(userId: string): boolean {
    return this.updatingPlatformUserIds.has(userId);
  }

  getUserAppRoleLabel(role?: AppRole | null): string {
    return getAppRoleLabel(role ?? AppRole.USER);
  }

  getPlatformUserRole(user: JUser): AppRole {
    return user.appRole ?? AppRole.USER;
  }

  onPlatformUserRoleChange(user: JUser, event: Event) {
    const nextRole = String((event.target as HTMLSelectElement)?.value ?? AppRole.USER) as AppRole;
    this.changePlatformUserRole(user, nextRole);
  }

  getProjectName(projectId: string): string {
    return this.projects.find((project) => project.id === projectId)?.name ?? 'Проект';
  }

  getProjectRole(project: JProjectSummary): string {
    return getProjectRoleLabel(project.currentUserRole);
  }

  getProjectIssueTotal(project: JProjectSummary): number {
    return this.issues.filter((issue) => issue.projectId === project.id).length;
  }

  getProjectDoneCount(project: JProjectSummary): number {
    return this.issues.filter(
      (issue) => issue.projectId === project.id && issue.statusCategory === 'done'
    ).length;
  }

  getProjectProgress(project: JProjectSummary): number {
    const total = this.getProjectIssueTotal(project);
    if (!total) {
      return 0;
    }

    return Math.round((this.getProjectDoneCount(project) / total) * 100);
  }

  getStatusName(statusId: string): string {
    return this.statuses.find((status) => status.id === statusId)?.name ?? 'Без статуса';
  }

  getStatusClass(issue: JIssue): string {
    switch (issue.statusCategory) {
      case 'done':
        return 'dashboard-badge dashboard-badge--success';
      case 'in_progress':
        return 'dashboard-badge dashboard-badge--accent';
      default:
        return 'dashboard-badge dashboard-badge--neutral';
    }
  }

  getTypeLabel(issue: JIssue): string {
    return issue.type === IssueType.EPIC ? 'Эпик' : 'Задача';
  }

  getTypeClass(issue: JIssue): string {
    return issue.type === IssueType.EPIC
      ? 'dashboard-type dashboard-type--epic'
      : 'dashboard-type dashboard-type--task';
  }

  getIssueSummary(issue: JIssue): string {
    const plainDescription = this.stripHtml(issue.description);
    return plainDescription || 'Описание задачи пока не добавлено.';
  }

  getDueLabel(issue: JIssue): string {
    if (!issue.dueDate) {
      return 'Без срока';
    }

    if (this.isOverdue(issue)) {
      return 'Просрочено';
    }

    if (this.isDueToday(issue)) {
      return 'Сегодня';
    }

    return 'Запланировано';
  }

  getDueClass(issue: JIssue): string {
    if (!issue.dueDate) {
      return 'dashboard-due dashboard-due--neutral';
    }

    if (this.isOverdue(issue)) {
      return 'dashboard-due dashboard-due--danger';
    }

    if (this.isDueToday(issue)) {
      return 'dashboard-due dashboard-due--warning';
    }

    return 'dashboard-due dashboard-due--neutral';
  }

  getActivityTitle(issue: JIssue): string {
    if (this.isOverdue(issue)) {
      return `Срок по задаче ${issue.key} уже истёк`;
    }

    if (issue.updatedAt !== issue.createdAt) {
      return `Задача ${issue.key} обновлена`;
    }

    return `Создана задача ${issue.key}`;
  }

  getActivityDescription(issue: JIssue): string {
    const statusName = this.getStatusName(issue.statusId);
    const projectName = this.getProjectName(issue.projectId);

    if (this.isOverdue(issue)) {
      return `${projectName} · ${statusName} · нужен пересмотр срока`;
    }

    return `${projectName} · ${statusName} · ${issue.title}`;
  }

  getActivityClass(issue: JIssue): string {
    if (this.isOverdue(issue)) {
      return 'dashboard-timeline__mark dashboard-timeline__mark--danger';
    }

    if (issue.updatedAt !== issue.createdAt) {
      return 'dashboard-timeline__mark dashboard-timeline__mark--accent';
    }

    return 'dashboard-timeline__mark dashboard-timeline__mark--success';
  }

  getIssueActivityDate(issue: JIssue): string {
    return issue.updatedAt !== issue.createdAt ? issue.updatedAt : issue.createdAt;
  }

  getDigestItemBadgeClass(item: DashboardDigestItem): string {
    return item.itemType === 'new_comment'
      ? 'dashboard-chip dashboard-chip--comment'
      : 'dashboard-chip dashboard-chip--update';
  }

  getDigestItemBadgeLabel(item: DashboardDigestItem): string {
    return item.itemType === 'new_comment' ? 'Комментарий' : 'Обновление';
  }

  getActionHistoryBadgeLabel(item: DashboardActionHistoryItem): string {
    switch (item.actionType) {
      case 'comment_added':
        return 'Комментарий';
      case 'worklog_added':
        return 'Запись времени';
      default:
        return 'Задача';
    }
  }

  isDueToday(issue: JIssue): boolean {
    const dueDate = this.parseDate(issue.dueDate);
    if (!dueDate) {
      return false;
    }

    const today = this.startOfDay(new Date());
    return dueDate.getTime() === today.getTime();
  }

  isDueThisWeek(issue: JIssue): boolean {
    const dueDate = this.parseDate(issue.dueDate);
    if (!dueDate || issue.statusCategory === 'done') {
      return false;
    }

    const today = this.startOfDay(new Date());
    const weekEnd = new Date(today);
    weekEnd.setDate(today.getDate() + 6);

    return dueDate.getTime() >= today.getTime() && dueDate.getTime() <= weekEnd.getTime();
  }

  isOverdue(issue: JIssue): boolean {
    const dueDate = this.parseDate(issue.dueDate);
    if (!dueDate || issue.statusCategory === 'done') {
      return false;
    }

    return dueDate.getTime() < this.startOfDay(new Date()).getTime();
  }

  private loadDashboard() {
    this.isLoading = true;
    this.errorMessage = '';

    this._dashboardService
      .getDashboardData()
      .pipe(
        finalize(() => {
          this.isLoading = false;
        })
      )
      .subscribe({
        next: (data) => {
          this.applyDashboardData(data);
        },
        error: (error) => {
          this.errorMessage = getApiErrorMessage(
            error,
            'Не удалось загрузить стартовую страницу.'
          );
        }
      });
  }

  private applyDashboardData(data: ProjectsDashboardData) {
    this.projects = data.projects;
    this.statuses = data.statuses;
    this.users = data.users;
    this.issues = data.issues;
    this.digestItems = data.digestItems;
    this.actionHistoryItems = data.actionHistoryItems;
    this.digestGeneratedAt = data.digestGeneratedAt;
    this._dashboardService.markDashboardSeen(data.digestGeneratedAt ?? undefined);
    if (this.canManagePlatformUsers) {
      this.loadPlatformUsers();
    } else {
      this.clearPlatformUsers();
    }

    if (
      this.selectedProjectId !== 'all' &&
      !this.projects.some((project) => project.id === this.selectedProjectId)
    ) {
      this.selectedProjectId = 'all';
    }
  }

  private matchesSearch(...values: Array<string | null | undefined>): boolean {
    const normalizedQuery = this.searchQuery.trim().toLowerCase();
    if (!normalizedQuery) {
      return true;
    }

    return values.some((value) =>
      String(value ?? '')
        .toLowerCase()
        .includes(normalizedQuery)
    );
  }

  private parseDate(value: string | null | undefined): Date | null {
    if (!value) {
      return null;
    }

    const nextValue = value.length === 10 ? `${value}T00:00:00` : value;
    const parsed = new Date(nextValue);
    return Number.isNaN(parsed.getTime()) ? null : this.startOfDay(parsed);
  }

  private startOfDay(date: Date): Date {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate());
  }

  private isUpdatedRecently(issue: JIssue): boolean {
    const issueUpdatedAt = new Date(issue.updatedAt).getTime();
    const sevenDaysAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
    return issueUpdatedAt >= sevenDaysAgo;
  }

  private stripHtml(value: string | null | undefined): string {
    return String(value ?? '')
      .replace(/<[^>]*>/g, ' ')
      .replace(/&nbsp;/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  private formatCreateError(error: any): string {
    if (error?.status === 409) {
      return getApiErrorMessage(error, 'Ключ проекта уже занят.');
    }

    return getApiErrorMessage(error, 'Не удалось создать проект.');
  }

  loadPlatformUsers() {
    if (!this.canManagePlatformUsers) {
      this.clearPlatformUsers();
      return;
    }

    this.isLoadingPlatformUsers = true;
    this.platformUsersErrorMessage = '';

    this._dashboardService
      .listPlatformUsers(
        this.platformUserSearchQuery,
        this.selectedPlatformRoleFilter === 'all' ? null : this.selectedPlatformRoleFilter
      )
      .pipe(
        finalize(() => {
          this.isLoadingPlatformUsers = false;
        })
      )
      .subscribe({
        next: (data) => {
          this.platformUsers = data.items;
        },
        error: (error) => {
          this.platformUsers = [];
          this.platformUsersErrorMessage = getApiErrorMessage(
            error,
            'Не удалось загрузить пользователей платформы.'
          );
        }
      });
  }

  private changePlatformUserRole(user: JUser, nextRole: AppRole) {
    if (this.isPlatformUserUpdating(user.id) || this.getPlatformUserRole(user) === nextRole) {
      return;
    }

    this.updatingPlatformUserIds.add(user.id);
    this.platformUsersErrorMessage = '';

    this._dashboardService
      .updateUserAppRole(user.id, nextRole)
      .pipe(
        finalize(() => {
          this.updatingPlatformUserIds.delete(user.id);
        })
      )
      .subscribe({
        next: (updatedUser) => {
          const matchesRoleFilter =
            this.selectedPlatformRoleFilter === 'all' ||
            this.selectedPlatformRoleFilter === this.getPlatformUserRole(updatedUser);
          this.platformUsers = matchesRoleFilter
            ? this.platformUsers.map((candidate) =>
                candidate.id === updatedUser.id ? updatedUser : candidate
              )
            : this.platformUsers.filter((candidate) => candidate.id !== updatedUser.id);

          if (this.isCurrentUser(updatedUser)) {
            this._authService.setUser(updatedUser);
            this.loadDashboard();
          }
        },
        error: (error) => {
          const message = getApiErrorMessage(error, 'Не удалось обновить роль на платформе.');
          this.platformUsersErrorMessage = message;
          this._notification.error(
            error?.status === 409
              ? 'Нельзя снять роль у последнего администратора платформы'
              : error?.status === 403
                ? 'Недостаточно прав для управления ролью платформы'
                : 'Не удалось обновить роль на платформе',
            message
          );
        }
      });
  }

  private clearPlatformUsers() {
    this.platformUsers = [];
    this.platformUsersErrorMessage = '';
    if (this.platformUsersSearchTimer) {
      clearTimeout(this.platformUsersSearchTimer);
      this.platformUsersSearchTimer = null;
    }
  }

  private restoreFocusWidgetState() {
    const raw = localStorage.getItem(this.focusWidgetStorageKey);
    if (!raw) {
      return;
    }

    try {
      this.isFocusWidgetCollapsed = Boolean(JSON.parse(raw));
    } catch {
      this.isFocusWidgetCollapsed = false;
    }
  }
}
