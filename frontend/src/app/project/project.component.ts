import { Component, OnInit } from '@angular/core';
import { getApiErrorMessage } from '@trungk18/core/utils/api-error';
import { ActivatedRoute, Router } from '@angular/router';
import { getProjectRoleLabel, ProjectRole } from '@trungk18/interface/role';
import { JUser } from '@trungk18/interface/user';
import { AuthQuery } from '@trungk18/project/auth/auth.query';
import { AuthService } from '@trungk18/project/auth/auth.service';
import { finalize } from 'rxjs/operators';
import { FilterQuery } from './state/filter/filter.query';
import { FilterService } from './state/filter/filter.service';
import { ProjectQuery } from './state/project/project.query';
import { ProjectService } from './state/project/project.service';
import { UntilDestroy, untilDestroyed } from '@ngneat/until-destroy';
import { distinctUntilChanged, filter, map } from 'rxjs/operators';
import { NzModalService } from 'ng-zorro-antd/modal';
import { AddIssueModalComponent } from './components/add-issue-modal/add-issue-modal.component';

@Component({
  selector: 'app-project',
  templateUrl: './project.component.html',
  styleUrls: ['./project.component.scss']
})
@UntilDestroy()
export class ProjectComponent implements OnInit {
  readonly defaultProfileInfo =
    'Работает с задачами, документацией и рабочим пространством проекта.';
  expanded: boolean;
  mobileNavOpen = false;
  errorMessage = '';
  isLoggingOut = false;
  searchQuery = '';
  private currentProjectId: string | null = null;

  constructor(
    private _projectService: ProjectService,
    private _route: ActivatedRoute,
    private _router: Router,
    public projectQuery: ProjectQuery,
    private _filterService: FilterService,
    private _filterQuery: FilterQuery,
    private _authService: AuthService,
    public authQuery: AuthQuery,
    private _modalService: NzModalService
  ) {
    this.expanded = window.matchMedia('(min-width: 1024px)').matches;
  }

  ngOnInit(): void {
    this._route.parent?.paramMap
      .pipe(
        map((params) => params.get('projectId')),
        filter((projectId): projectId is string => !!projectId),
        distinctUntilChanged(),
        untilDestroyed(this)
      )
      .subscribe((projectId) => {
        this.currentProjectId = projectId;
        this.errorMessage = '';
        this._filterService.resetAll();
        this._projectService.loadProjectIfNeeded(projectId);
      });

    this.projectQuery.error$.pipe(untilDestroyed(this)).subscribe((error) => {
      this.errorMessage = error ? getApiErrorMessage(error, 'Не удалось открыть проект.') : '';
    });

    this._filterQuery.all$
      .pipe(
        map((filters) => filters.q || ''),
        distinctUntilChanged(),
        untilDestroyed(this)
      )
      .subscribe((searchQuery) => {
        this.searchQuery = searchQuery;
      });

    this.handleResize();
  }

  get isBoardRoute(): boolean {
    return this._router.url.includes('/board');
  }

  handleResize() {
    const match = window.matchMedia('(min-width: 1024px)');
    this.expanded = match.matches;
    this.mobileNavOpen = false;
    match.addEventListener('change', (e) => {
      this.expanded = e.matches;
      if (e.matches) {
        this.mobileNavOpen = false;
      }
    });
  }

  retryLoadProject() {
    if (!this.currentProjectId) {
      return;
    }

    this.errorMessage = '';
    this._filterService.resetAll();
    this._projectService.loadProject(this.currentProjectId);
  }

  onSearchInput(event: Event) {
    this.onSearchQueryChange(String((event.target as HTMLInputElement)?.value ?? ''));
  }

  onSearchQueryChange(query: string) {
    this._filterService.updateSearchTerm(query);
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

    return (user.name || user.email || '?').trim().charAt(0).toUpperCase() || '?';
  }

  getCurrentUserProjectRole(role: ProjectRole | null): string {
    return getProjectRoleLabel(role);
  }

  getProjectUserRole(userId: string): string {
    const projectMember = this.projectQuery
      .getValue()
      .users.find((member) => member.id === userId);

    return getProjectRoleLabel(projectMember?.projectRole ?? null);
    /*
    switch (projectMember?.projectRole) {
      case 'project_owner':
        return 'Владелец проекта';
      case 'project_admin':
        return 'Администратор проекта';
      case 'project_member':
        return 'Участник проекта';
      default:
        return 'Участник платформы';
    }
    */
  }

  getProjectProfileInfo(projectName: string, projectKey: string): string {
    const normalizedProjectName = projectName?.trim();
    const normalizedProjectKey = projectKey?.trim();

    if (normalizedProjectName && normalizedProjectKey) {
      return `Участвует в проекте ${normalizedProjectName} (${normalizedProjectKey}).`;
    }

    if (normalizedProjectName) {
      return `Участвует в проекте ${normalizedProjectName}.`;
    }

    return this.defaultProfileInfo;
  }

  manualToggle() {
    if (window.matchMedia('(min-width: 1024px)').matches) {
      this.expanded = !this.expanded;
      return;
    }

    this.mobileNavOpen = !this.mobileNavOpen;
  }

  closeMobileNavigation() {
    if (!window.matchMedia('(min-width: 1024px)').matches) {
      this.mobileNavOpen = false;
    }
  }

  openCreateIssueModal() {
    if (!this.isBoardRoute) {
      return;
    }

    this._modalService.create({
      nzContent: AddIssueModalComponent,
      nzClosable: false,
      nzFooter: null,
      nzWidth: 700
    });
  }
}
