import { Component, OnInit } from '@angular/core';
import {
  UntypedFormBuilder,
  UntypedFormControl,
  UntypedFormGroup,
  Validators
} from '@angular/forms';
import { Router } from '@angular/router';
import { UntilDestroy, untilDestroyed } from '@ngneat/until-destroy';
import { getApiErrorMessage } from '@trungk18/core/utils/api-error';
import { NoWhitespaceValidator } from '@trungk18/core/validators/no-whitespace.validator';
import { JProject } from '@trungk18/interface/project';
import {
  getProjectRoleLabel as getProjectRoleDisplayLabel,
  isAdminProjectRole,
  ProjectRole
} from '@trungk18/interface/role';
import { JUser } from '@trungk18/interface/user';
import { AuthQuery } from '@trungk18/project/auth/auth.query';
import {
  ProjectService,
  UpdateProjectSettingsPayload
} from '@trungk18/project/state/project/project.service';
import { ProjectQuery } from '@trungk18/project/state/project/project.query';
import { NzNotificationService } from 'ng-zorro-antd/notification';
import { debounceTime, distinctUntilChanged, finalize } from 'rxjs/operators';

interface ProjectSettingsSnapshot {
  id: string;
  name: string;
  description: string;
}

@Component({
  templateUrl: './settings.component.html',
  styleUrls: ['./settings.component.scss']
})
@UntilDestroy()
export class SettingsComponent implements OnInit {
  project: JProject;
  projectForm: UntypedFormGroup;
  searchControl = new UntypedFormControl('');
  projectRoles: ProjectRole[];
  availableUsers: JUser[] = [];
  pendingRoles: Record<string, ProjectRole> = {};
  isSavingProject = false;
  isDeletingProject = false;
  isSavingOnboardingMode = false;
  isSavingOnboardingAssignees = false;
  isSearchingUsers = false;
  projectErrorMessage = '';
  projectDeleteErrorMessage = '';
  onboardingErrorMessage = '';
  membersErrorMessage = '';

  private workingMemberIds = new Set<string>();
  private lastProjectId: string | null = null;
  private lastSettingsSnapshot: ProjectSettingsSnapshot | null = null;
  private currentSearchRequestId = 0;

  get breadcrumbs(): string[] {
    return ['Проекты', this.project?.name, 'Настройки'];
  }

  get members(): JUser[] {
    return this.project?.users ?? [];
  }

  get currentUserId(): string | null {
    return this._authQuery.getValue().user?.id ?? null;
  }

  get directAdminCount(): number {
    return this.members.filter((user) => user.projectRole === ProjectRole.ADMIN_PROJECT).length;
  }

  get onboardingAssigneeIds(): string[] {
    return this.project?.onboardingAssigneeIds ?? [];
  }

  constructor(
    private _projectQuery: ProjectQuery,
    private _projectService: ProjectService,
    private _notification: NzNotificationService,
    private _fb: UntypedFormBuilder,
    private _router: Router,
    private _authQuery: AuthQuery
  ) {
    this.projectRoles = [ProjectRole.ADMIN_PROJECT, ProjectRole.USER];
  }

  ngOnInit(): void {
    this.initForm();

    this._projectQuery.project$
      .pipe(untilDestroyed(this))
      .subscribe((project) => {
        this.project = project;
        this.syncProjectForm(project);
        this.cleanupPendingRoles();

        if (!project?.id) {
          return;
        }

        if (this.lastProjectId !== project.id) {
          this.lastProjectId = project.id;
          this.refreshAvailableUsers();
        }

        if (!isAdminProjectRole(project.currentUserRole)) {
          this.availableUsers = [];
          this.navigateOutOfSettings(project);
        }
      });

    this.searchControl.valueChanges
      .pipe(
        debounceTime(250),
        distinctUntilChanged(),
        untilDestroyed(this)
      )
      .subscribe(() => {
        this.refreshAvailableUsers();
      });
  }

  initForm() {
    this.projectForm = this._fb.group({
      name: [
        '',
        [Validators.required, Validators.maxLength(200), NoWhitespaceValidator()]
      ],
      description: ['', Validators.maxLength(5000)]
    });
  }

  submitForm() {
    if (this.projectForm.invalid) {
      this.projectForm.markAllAsTouched();
      return;
    }

    const payload = this.projectForm.getRawValue() as UpdateProjectSettingsPayload;
    this.isSavingProject = true;
    this.projectErrorMessage = '';
    this.projectDeleteErrorMessage = '';

    this._projectService
      .updateProjectSettings(payload)
      .pipe(
        finalize(() => {
          this.isSavingProject = false;
        })
      )
      .subscribe({
        next: () => {
          this._notification.success(
            'Настройки проекта сохранены',
            'Параметры проекта успешно обновлены.'
          );
        },
        error: (error) => {
          this.projectErrorMessage = this.formatProjectError(error);
          this.handleForbidden(error);
        }
      });
  }

  cancel() {
    if (!this.project?.id) {
      this._router.navigate(['/projects']);
      return;
    }

    this._router.navigate(['/projects', this.project.id, 'board']);
  }

  deleteProject() {
    if (!this.project?.id || this.isDeletingProject) {
      return;
    }

    const confirmed = window.confirm(
      'Удалить проект? Это действие доступно только для проекта без задач и не может быть отменено.'
    );
    if (!confirmed) {
      return;
    }

    this.projectDeleteErrorMessage = '';
    this.isDeletingProject = true;
    const projectLabel = this.project.name || this.project.key;

    this._projectService
      .deleteProject(this.project.id)
      .pipe(
        finalize(() => {
          this.isDeletingProject = false;
        })
      )
      .subscribe({
        next: () => {
          this._notification.success(
            'Проект удален',
            `Проект ${projectLabel} больше не отображается в списках.`
          );
          this._router.navigate(['/projects']);
        },
        error: (error) => {
          this.projectDeleteErrorMessage = this.formatProjectDeleteError(error);
          this.handleForbidden(error);
        }
      });
  }

  toggleNewEmployeeMode(event: Event) {
    const target = event.target as HTMLInputElement;
    const nextValue = target.checked;
    const currentValue = !!this.project?.newEmployeeMode;
    const scrollTop = window.scrollY || document.documentElement.scrollTop || 0;

    if (!this.project?.id || this.isSavingOnboardingMode || nextValue === currentValue) {
      return;
    }

    this.onboardingErrorMessage = '';
    this.isSavingOnboardingMode = true;

    this._projectService
      .updateOnboardingPreferences(nextValue)
      .pipe(
        finalize(() => {
          this.isSavingOnboardingMode = false;
          requestAnimationFrame(() => window.scrollTo({ top: scrollTop }));
        })
      )
      .subscribe({
        next: (enabled) => {
          this._notification.success(
            enabled ? 'Режим нового сотрудника включен' : 'Режим нового сотрудника выключен',
            enabled
              ? 'Onboarding-подборка и пункт в навигации стали доступны.'
              : 'Пункт onboarding скрыт до повторного включения.'
          );
        },
        error: (error) => {
          target.checked = currentValue;
          this.onboardingErrorMessage = getApiErrorMessage(
            error,
            'Не удалось обновить режим нового сотрудника.'
          );
          this.handleForbidden(error);
        }
      });
  }

  openOnboarding() {
    if (!this.project?.id) {
      return;
    }

    this._router.navigate(['/projects', this.project.id, 'onboarding']);
  }

  isOnboardingAssignee(userId: string): boolean {
    return this.onboardingAssigneeIds.includes(userId);
  }

  toggleOnboardingAssignee(user: JUser, event: Event): void {
    if (this.isSavingOnboardingAssignees || !this.project?.id) {
      return;
    }

    const target = event.target as HTMLInputElement;
    const shouldAssign = !!target.checked;
    const current = this.onboardingAssigneeIds;
    const next = shouldAssign
      ? Array.from(new Set([...current, user.id]))
      : current.filter((userId) => userId !== user.id);

    this.updateOnboardingAssignees(next, target, shouldAssign, user);
  }

  addUser(user: JUser) {
    if (this.isMemberBusy(user.id)) {
      return;
    }

    const role = this.getPendingRole(user.id);
    this.membersErrorMessage = '';
    this.setMemberBusy(user.id, true);

    this._projectService
      .addProjectUser(user, role)
      .pipe(
        finalize(() => {
          this.setMemberBusy(user.id, false);
        })
      )
      .subscribe({
        next: () => {
          delete this.pendingRoles[user.id];
          this.availableUsers = this.availableUsers.filter((candidate) => candidate.id !== user.id);
          this.cleanupPendingRoles();
          this._notification.success(
            'Участник добавлен',
            `${this.getUserLabel(user)} добавлен в проект.`
          );
          this.refreshAvailableUsers();
        },
        error: (error) => {
          this.membersErrorMessage = this.formatMembersError(
            error,
            'Не удалось добавить выбранного пользователя.'
          );
          this.handleForbidden(error);
        }
      });
  }

  changeMemberRole(user: JUser, nextRole: ProjectRole) {
    if (
      !nextRole ||
      this.isMemberBusy(user.id) ||
      user.projectRole === nextRole ||
      this.isLastDirectAdmin(user)
    ) {
      return;
    }

    this.membersErrorMessage = '';
    this.setMemberBusy(user.id, true);

    this._projectService
      .updateProjectUserRole(user.id, nextRole)
      .pipe(
        finalize(() => {
          this.setMemberBusy(user.id, false);
        })
      )
      .subscribe({
        next: () => {
          this._notification.success(
            'Роль обновлена',
            `Для пользователя ${this.getUserLabel(user)} установлена роль ${this.getProjectRoleLabel(nextRole).toLowerCase()}.`
          );
        },
        error: (error) => {
          this.membersErrorMessage = this.formatMembersError(
            error,
            'Не удалось изменить роль участника.'
          );
          this.handleForbidden(error);
        }
      });
  }

  removeUser(user: JUser) {
    if (this.isMemberBusy(user.id) || this.isLastDirectAdmin(user)) {
      return;
    }

    this.membersErrorMessage = '';
    this.setMemberBusy(user.id, true);

    this._projectService
      .removeProjectUser(user.id)
      .pipe(
        finalize(() => {
          this.setMemberBusy(user.id, false);
        })
      )
      .subscribe({
        next: () => {
          this._notification.success(
            'Участник удален',
            `${this.getUserLabel(user)} удален из проекта.`
          );
          this.refreshAvailableUsers();
        },
        error: (error) => {
          this.membersErrorMessage = this.formatMembersError(
            error,
            'Не удалось удалить выбранного пользователя.'
          );
          this.handleForbidden(error);
        }
      });
  }

  trackByUserId(_index: number, user: JUser): string {
    return user.id;
  }

  getProjectRoleLabel(role?: ProjectRole | null): string {
    return getProjectRoleDisplayLabel(role);
  }

  getPendingRole(userId: string): ProjectRole {
    return this.pendingRoles[userId] ?? ProjectRole.USER;
  }

  setPendingRole(userId: string, role: ProjectRole) {
    this.pendingRoles[userId] = role;
  }

  isMemberBusy(userId: string): boolean {
    return this.workingMemberIds.has(userId);
  }

  isLastDirectAdmin(user: JUser): boolean {
    return user.projectRole === ProjectRole.ADMIN_PROJECT && this.directAdminCount <= 1;
  }

  isCurrentUser(user: JUser): boolean {
    return !!this.currentUserId && user.id === this.currentUserId;
  }

  getUserLabel(user: JUser): string {
    return user.name || user.email || 'Этот пользователь';
  }

  private syncProjectForm(project: JProject) {
    if (!project?.id) {
      return;
    }

    const nextSnapshot = this.createSettingsSnapshot(project);
    if (this.isSameSnapshot(this.lastSettingsSnapshot, nextSnapshot)) {
      return;
    }

    this.projectForm.patchValue(nextSnapshot, { emitEvent: false });
    this.projectForm.markAsPristine();
    this.projectForm.markAsUntouched();
    this.lastSettingsSnapshot = nextSnapshot;
  }

  private refreshAvailableUsers() {
    if (!this.project?.id || !isAdminProjectRole(this.project.currentUserRole)) {
      this.availableUsers = [];
      this.cleanupPendingRoles();
      return;
    }

    const requestId = ++this.currentSearchRequestId;
    this.isSearchingUsers = true;
    this.membersErrorMessage = '';

    this._projectService
      .searchAvailableProjectUsers(String(this.searchControl.value ?? ''))
      .pipe(
        finalize(() => {
          if (requestId === this.currentSearchRequestId) {
            this.isSearchingUsers = false;
          }
        })
      )
      .subscribe({
        next: (users) => {
          if (requestId !== this.currentSearchRequestId) {
            return;
          }

          this.availableUsers = users;
          this.cleanupPendingRoles();
        },
        error: (error) => {
          if (requestId !== this.currentSearchRequestId) {
            return;
          }

          this.availableUsers = [];
          this.cleanupPendingRoles();
          this.membersErrorMessage = this.formatMembersError(
            error,
            'Не удалось выполнить поиск пользователей.'
          );
          this.handleForbidden(error);
        }
      });
  }

  private cleanupPendingRoles() {
    const availableIds = new Set(this.availableUsers.map((user) => user.id));
    Object.keys(this.pendingRoles).forEach((userId) => {
      if (!availableIds.has(userId)) {
        delete this.pendingRoles[userId];
      }
    });

    this.availableUsers.forEach((user) => {
      this.pendingRoles[user.id] = this.pendingRoles[user.id] ?? ProjectRole.USER;
    });
  }

  private setMemberBusy(userId: string, isBusy: boolean) {
    if (isBusy) {
      this.workingMemberIds.add(userId);
      return;
    }

    this.workingMemberIds.delete(userId);
  }

  private createSettingsSnapshot(project: JProject): ProjectSettingsSnapshot {
    return {
      id: project.id,
      name: project.name ?? '',
      description: project.description ?? ''
    };
  }

  private isSameSnapshot(
    left: ProjectSettingsSnapshot | null,
    right: ProjectSettingsSnapshot
  ): boolean {
    return !!left &&
      left.id === right.id &&
      left.name === right.name &&
      left.description === right.description;
  }

  private formatProjectError(error: any): string {
    if (error?.status === 403) {
      return 'Для изменения настроек проекта требуется роль admin_project.';
    }

    return getApiErrorMessage(error, 'Не удалось сохранить настройки проекта.');
  }

  private formatProjectDeleteError(error: any): string {
    if (error?.status === 403) {
      return 'Для удаления проекта требуется роль admin_project.';
    }

    if (error?.status === 409) {
      return 'Проект содержит задачи. Сначала удалите или перенесите их, затем повторите удаление проекта.';
    }

    return getApiErrorMessage(error, 'Не удалось удалить проект.');
  }

  private formatMembersError(error: any, fallback: string): string {
    if (error?.status === 403) {
      return 'Для управления участниками требуется роль admin_project.';
    }

    if (
      error?.status === 409 &&
      String(error?.error?.detail ?? '').includes('admin_project')
    ) {
      return 'Последнего участника с ролью «Администратор проекта» нельзя удалить или понизить.';
    }

    return getApiErrorMessage(error, fallback);
  }

  private handleForbidden(error: any) {
    if (error?.status !== 403) {
      return;
    }

    const message = getApiErrorMessage(
      error,
      'У вас больше нет доступа к настройкам проекта.'
    );
    this._notification.error('Нет доступа к настройкам проекта', message);

    const detail = String(error?.error?.detail ?? '').toLowerCase();
    if (detail.includes('no access to project')) {
      this._router.navigate(['/projects']);
      return;
    }

    if (this.project?.id) {
      this._router.navigate(['/projects', this.project.id, 'board']);
      return;
    }

    this._router.navigate(['/projects']);
  }

  private navigateOutOfSettings(project: JProject) {
    if (!project?.id) {
      this._router.navigate(['/projects']);
      return;
    }

    if (project.currentUserRole === ProjectRole.USER) {
      this._router.navigate(['/projects', project.id, 'board']);
      return;
    }

    this._router.navigate(['/projects']);
  }

  private updateOnboardingAssignees(
    nextAssigneeIds: string[],
    target: HTMLInputElement,
    shouldAssign: boolean,
    user: JUser
  ): void {
    this.onboardingErrorMessage = '';
    this.isSavingOnboardingAssignees = true;

    this._projectService
      .updateOnboardingAssignees(nextAssigneeIds)
      .pipe(
        finalize(() => {
          this.isSavingOnboardingAssignees = false;
        })
      )
      .subscribe({
        next: () => {
          this._notification.success(
            shouldAssign ? 'Onboarding назначен' : 'Onboarding снят',
            shouldAssign
              ? `${this.getUserLabel(user)} будет видеть раздел New Employee.`
              : `${this.getUserLabel(user)} больше не видит раздел New Employee.`
          );
        },
        error: (error) => {
          target.checked = !shouldAssign;
          this.onboardingErrorMessage = getApiErrorMessage(
            error,
            'Не удалось обновить назначение onboarding.'
          );
          this.handleForbidden(error);
        }
      });
  }
}
