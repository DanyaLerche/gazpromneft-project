import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { UntilDestroy, untilDestroyed } from '@ngneat/until-destroy';
import { getApiErrorMessage } from '@trungk18/core/utils/api-error';
import {
  JOnboardingIssueItem,
  JOnboardingPersonItem,
  JOnboardingReadItem,
  JOnboardingRecommendations
} from '@trungk18/interface/onboarding';
import { JProject } from '@trungk18/interface/project';
import { isAdminProjectRole } from '@trungk18/interface/role';
import { JUser } from '@trungk18/interface/user';
import { ProjectQuery } from '@trungk18/project/state/project/project.query';
import { ProjectService } from '@trungk18/project/state/project/project.service';
import { NzNotificationService } from 'ng-zorro-antd/notification';
import { combineLatest } from 'rxjs';
import { distinctUntilChanged, filter, finalize, map } from 'rxjs/operators';

@Component({
  templateUrl: './onboarding.component.html',
  styleUrls: ['./onboarding.component.scss']
})
@UntilDestroy()
export class OnboardingComponent implements OnInit {
  project: JProject;
  projectId: string | null = null;
  recommendations: JOnboardingRecommendations | null = null;
  isLoading = false;
  isRefreshing = false;
  isSavingAssignees = false;
  errorMessage = '';
  assigneeErrorMessage = '';
  selectedAssigneeId = '';

  private lastLoadedProjectId: string | null = null;

  get breadcrumbs(): string[] {
    return ['Проекты', this.project?.name || '...', 'Новый сотрудник'];
  }

  get isProjectAdmin(): boolean {
    return isAdminProjectRole(this.project?.currentUserRole);
  }

  get onboardingAssigneeIds(): string[] {
    return this.project?.onboardingAssigneeIds ?? [];
  }

  get onboardingAssignees(): JUser[] {
    const assigneeIds = new Set(this.onboardingAssigneeIds);
    return (this.project?.users ?? []).filter((user) => assigneeIds.has(user.id));
  }

  get availableAssigneeUsers(): JUser[] {
    const assigneeIds = new Set(this.onboardingAssigneeIds);
    return (this.project?.users ?? []).filter((user) => !assigneeIds.has(user.id));
  }

  get reads(): JOnboardingReadItem[] {
    return this.recommendations?.reads ?? [];
  }

  get issuesToReview(): JOnboardingIssueItem[] {
    return this.recommendations?.issuesToReview ?? [];
  }

  get keyPeople(): JOnboardingPersonItem[] {
    return this.recommendations?.keyPeople ?? [];
  }

  get hasAnyRecommendations(): boolean {
    return this.reads.length > 0 || this.issuesToReview.length > 0 || this.keyPeople.length > 0;
  }

  constructor(
    private _route: ActivatedRoute,
    private _projectQuery: ProjectQuery,
    private _projectService: ProjectService,
    private _notification: NzNotificationService
  ) {}

  ngOnInit(): void {
    this._projectQuery.project$
      .pipe(untilDestroyed(this))
      .subscribe((project) => {
        this.project = project;
      });

    const routeProjectId$ = this._route.parent?.paramMap.pipe(
      map((params) => params.get('projectId')),
      filter((projectId): projectId is string => !!projectId),
      distinctUntilChanged()
    );

    if (!routeProjectId$) {
      return;
    }

    combineLatest([
      routeProjectId$,
      this._projectQuery.project$.pipe(
        map((project) => project?.id ?? ''),
        distinctUntilChanged()
      )
    ])
      .pipe(
        filter(([routeProjectId, projectId]) => projectId === routeProjectId),
        untilDestroyed(this)
      )
      .subscribe(([routeProjectId]) => {
        this.projectId = routeProjectId;

        if (this.lastLoadedProjectId === routeProjectId && this.recommendations) {
          return;
        }

        this.lastLoadedProjectId = routeProjectId;
        this.loadRecommendations();
      });
  }

  trackByRead(_index: number, item: JOnboardingReadItem): string {
    return item.pageId;
  }

  trackByIssue(_index: number, item: JOnboardingIssueItem): string {
    return item.issueId;
  }

  trackByPerson(_index: number, item: JOnboardingPersonItem): string {
    return item.userId;
  }

  refreshRecommendations(): void {
    this.loadRecommendations(true);
  }

  personMailto(person: JOnboardingPersonItem): string | null {
    return person.email ? `mailto:${person.email}` : null;
  }

  selectOnboardingAssignee(userId: string): void {
    this.selectedAssigneeId = userId;
  }

  addOnboardingAssignee(): void {
    if (!this.selectedAssigneeId || this.isSavingAssignees || !this.isProjectAdmin) {
      return;
    }

    const nextAssigneeIds = Array.from(
      new Set([...this.onboardingAssigneeIds, this.selectedAssigneeId])
    );
    this.updateOnboardingAssignees(nextAssigneeIds);
  }

  removeOnboardingAssignee(userId: string): void {
    if (this.isSavingAssignees || !this.isProjectAdmin) {
      return;
    }

    const nextAssigneeIds = this.onboardingAssigneeIds.filter((assigneeId) => assigneeId !== userId);
    this.updateOnboardingAssignees(nextAssigneeIds);
  }

  private loadRecommendations(force = false): void {
    if (!this.projectId) {
      return;
    }

    const hasExistingData = !!this.recommendations;
    this.errorMessage = '';
    this.isLoading = !hasExistingData;
    this.isRefreshing = hasExistingData;

    this._projectService
      .getOnboardingRecommendations(force)
      .pipe(
        finalize(() => {
          this.isLoading = false;
          this.isRefreshing = false;
        }),
        untilDestroyed(this)
      )
      .subscribe({
        next: (recommendations) => {
          this.recommendations = recommendations;
        },
        error: (error) => {
          this.errorMessage = getApiErrorMessage(
            error,
            'Не удалось построить onboarding-рекомендации.'
          );
        }
      });
  }

  private updateOnboardingAssignees(nextAssigneeIds: string[]): void {
    this.assigneeErrorMessage = '';
    this.isSavingAssignees = true;

    this._projectService
      .updateOnboardingAssignees(nextAssigneeIds)
      .pipe(
        finalize(() => {
          this.isSavingAssignees = false;
        }),
        untilDestroyed(this)
      )
      .subscribe({
        next: (assignees) => {
          this.selectedAssigneeId = '';
          this._notification.success(
            'Назначения onboarding обновлены',
            `Выбрано пользователей: ${assignees.length}.`
          );
        },
        error: (error) => {
          this.assigneeErrorMessage = getApiErrorMessage(
            error,
            'Не удалось обновить назначение onboarding.'
          );
        }
      });
  }
}
