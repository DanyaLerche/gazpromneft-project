import { FormBuilder } from '@angular/forms';
import { AppRole, ProjectRole } from '@trungk18/interface/role';
import { of } from 'rxjs';
import { ProjectsPageComponent } from './projects-page.component';

describe('ProjectsPageComponent', () => {
  function createComponent(appRole: AppRole, currentUserRole: ProjectRole | null = null) {
    const dashboardService: any = {
      getDashboardData: jasmine.createSpy('getDashboardData').and.returnValue(
        of({
          projects: [],
          issues: [],
          statuses: [],
          users: [],
          total: 0,
          digestItems: [],
          actionHistoryItems: [],
          digestGeneratedAt: null
        })
      ),
      markDashboardSeen: jasmine.createSpy('markDashboardSeen'),
      listPlatformUsers: jasmine.createSpy('listPlatformUsers').and.returnValue(
        of({ items: [], total: 0 })
      ),
      updateUserAppRole: jasmine.createSpy('updateUserAppRole').and.returnValue(
        of({
          id: 'user-1',
          name: 'User',
          email: 'user@example.com',
          appRole,
          isActive: true
        })
      )
    };
    const projectService: any = {
      createProject: jasmine.createSpy('createProject').and.returnValue(of({}))
    };
    const authService: any = {
      logout: jasmine.createSpy('logout').and.returnValue(of(void 0)),
      setUser: jasmine.createSpy('setUser')
    };
    const notificationService: any = {
      error: jasmine.createSpy('error')
    };
    const authQuery: any = {
      getValue: jasmine.createSpy('getValue').and.returnValue({
        user: {
          id: 'user-1',
          appRole
        }
      })
    };
    const focusMode: any = {
      enabled$: of(false),
      isEnabled: jasmine.createSpy('isEnabled').and.returnValue(false),
      toggle: jasmine.createSpy('toggle')
    };

    const component = new ProjectsPageComponent(
      dashboardService,
      projectService,
      new FormBuilder(),
      authService,
      notificationService,
      authQuery,
      focusMode
    );

    component.projects = currentUserRole
      ? [
          {
            id: 'project-1',
            key: 'PRJ',
            name: 'Project',
            createdBy: 'user-1',
            createdAt: '2026-01-01T00:00:00Z',
            currentUserRole
          }
        ]
      : [];

    return {
      component,
      dashboardService,
      authService,
      notificationService,
      authQuery
    };
  }

  it('shows create-project actions for an authenticated plain user', () => {
    const { component } = createComponent(AppRole.USER);

    expect(component.canCreateProjects).toBeTrue();

    component.openCreateForm();

    expect(component.showCreateForm).toBeTrue();
  });

  it('shows create-project actions for an app admin', () => {
    const { component } = createComponent(AppRole.ADMIN_APP);

    expect(component.canCreateProjects).toBeTrue();
    expect(component.canManagePlatformUsers).toBeTrue();

    component.openCreateForm();

    expect(component.showCreateForm).toBeTrue();
  });

  it('shows create-project actions for a project admin', () => {
    const { component } = createComponent(AppRole.USER, ProjectRole.ADMIN_PROJECT);

    expect(component.canCreateProjects).toBeTrue();
    expect(component.canManagePlatformUsers).toBeFalse();
  });

  it('loads platform users on init only for admin_app', () => {
    const admin = createComponent(AppRole.ADMIN_APP);
    admin.component.ngOnInit();

    expect(admin.dashboardService.getDashboardData).toHaveBeenCalled();
    expect(admin.dashboardService.listPlatformUsers).toHaveBeenCalled();

    const plainUser = createComponent(AppRole.USER);
    plainUser.component.ngOnInit();

    expect(plainUser.dashboardService.getDashboardData).toHaveBeenCalled();
    expect(plainUser.dashboardService.listPlatformUsers).not.toHaveBeenCalled();
  });

  it('updates platform-user list after a successful role change without reloading the dashboard', () => {
    const { component, dashboardService, authService } = createComponent(AppRole.ADMIN_APP);
    const managedUser = {
      id: 'user-2',
      name: 'Managed User',
      email: 'managed@example.com',
      appRole: AppRole.USER,
      isActive: true
    };
    component.platformUsers = [managedUser];
    component.selectedPlatformRoleFilter = AppRole.USER;
    dashboardService.updateUserAppRole.and.returnValue(
      of({
        ...managedUser,
        appRole: AppRole.ADMIN_APP
      })
    );

    component.onPlatformUserRoleChange(managedUser, {
      target: { value: AppRole.ADMIN_APP }
    } as unknown as Event);

    expect(component.platformUsers).toEqual([]);
    expect(authService.setUser).not.toHaveBeenCalled();
    expect(dashboardService.getDashboardData).not.toHaveBeenCalled();
  });
});
