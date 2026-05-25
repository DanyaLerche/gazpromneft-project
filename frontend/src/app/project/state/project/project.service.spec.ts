import { ProjectCategory } from '@trungk18/interface/project';
import { AppRole, ProjectRole } from '@trungk18/interface/role';
import { JUser } from '@trungk18/interface/user';
import { of } from 'rxjs';
import { createInitialState } from './project.store';
import { ProjectService } from './project.service';

describe('ProjectService', () => {
  let service: ProjectService;
  let state = createInitialState();

  const httpClient: any = {
    get: jasmine.createSpy('get'),
    post: jasmine.createSpy('post'),
    patch: jasmine.createSpy('patch'),
    delete: jasmine.createSpy('delete')
  };
  const projectStore: any = {
    setLoading: jasmine.createSpy('setLoading').and.callThrough(),
    setError: jasmine.createSpy('setError').and.callThrough(),
    getValue: jasmine.createSpy('getValue').and.callFake(() => state),
    update: jasmine.createSpy('update').and.callFake((updater: (currentState: typeof state) => typeof state) => {
      state = updater(state);
      return state;
    })
  };
  const notificationService: any = {
    error: jasmine.createSpy('error').and.callThrough()
  };
  const profilePreferencesService: any = {
    hydrateUser: jasmine.createSpy('hydrateUser').and.callFake((user: any) => user)
  };
  const authQuery: any = {
    getValue: jasmine.createSpy('getValue').and.callFake(() => ({
      user: {
        id: 'current-user',
        appRole: AppRole.USER
      }
    }))
  };

  function createUser(
    id: string,
    name: string,
    email: string,
    projectRole?: ProjectRole
  ): JUser {
    return {
      id,
      name,
      email,
      appRole: AppRole.USER,
      projectRole
    };
  }

  beforeEach(() => {
    state = {
      ...createInitialState(),
      id: 'project-1',
      key: 'PRJ',
      name: 'Project',
      createdBy: 'current-user',
      createdAt: '2026-01-01T00:00:00Z',
      updateAt: '2026-01-01T00:00:00Z',
      currentUserRole: ProjectRole.ADMIN_PROJECT,
      users: [
        createUser('current-user', 'Owner', 'owner@example.com', ProjectRole.ADMIN_PROJECT)
      ]
    };

    httpClient.post.calls.reset();
    httpClient.patch.calls.reset();
    httpClient.delete.calls.reset();
    httpClient.get.calls.reset();
    projectStore.setLoading.calls.reset();
    projectStore.setError.calls.reset();
    projectStore.getValue.calls.reset();
    projectStore.update.calls.reset();
    notificationService.error.calls.reset();
    profilePreferencesService.hydrateUser.calls.reset();
    authQuery.getValue.calls.reset();

    service = new ProjectService(
      httpClient,
      projectStore,
      notificationService,
      profilePreferencesService,
      authQuery
    );
    service.baseUrl = '';
    (service as any).currentProjectIdValue = 'project-1';
  });

  it('should be able to set loading ', () => {
    service.setLoading(true);
    expect(projectStore.setLoading).toHaveBeenCalledWith(true);
  });

  it('updates project settings and patches the current project state', () => {
    httpClient.patch.and.returnValue(
      of({
        project: {
          id: 'project-1',
          key: 'PRJ',
          name: 'Renamed Project',
          description: 'Refined scope',
          category: ProjectCategory.BUSINESS,
          created_by: 'current-user',
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-02T00:00:00Z',
          current_user_role: ProjectRole.ADMIN_PROJECT
        }
      })
    );

    let result: any;
    service
      .updateProjectSettings({
        name: '  Renamed Project  ',
        description: '  Refined scope  ',
        category: ProjectCategory.BUSINESS
      })
      .subscribe((value) => {
        result = value;
      });

    expect(httpClient.patch).toHaveBeenCalledWith('/projects/project-1', {
      name: 'Renamed Project',
      description: 'Refined scope',
      category: ProjectCategory.BUSINESS
    });
    expect(state.name).toBe('Renamed Project');
    expect(state.description).toBe('Refined scope');
    expect(state.category).toBe(ProjectCategory.BUSINESS);
    expect(state.updateAt).toBe('2026-01-02T00:00:00Z');
    expect(result).toBe(state);
  });

  it('adds a project member to the local state', () => {
    const candidate = createUser('member-1', 'New Member', 'member@example.com');
    httpClient.post.and.returnValue(of({}));

    let addedUser: JUser | undefined;
    service.addProjectUser(candidate, ProjectRole.USER).subscribe((value) => {
      addedUser = value;
    });

    expect(httpClient.post).toHaveBeenCalledWith('/projects/project-1/users', {
      user_id: 'member-1',
      role: ProjectRole.USER
    });
    expect(addedUser?.projectRole).toBe(ProjectRole.USER);
    expect(state.users.some((user) => user.id === 'member-1')).toBeTrue();
  });

  it('promotes a project member in the local state', () => {
    state = {
      ...state,
      users: [
        ...state.users,
        createUser('member-1', 'Existing Member', 'member@example.com', ProjectRole.USER)
      ]
    };
    httpClient.patch.and.returnValue(of({}));

    let updatedUser: JUser | undefined;
    service.updateProjectUserRole('member-1', ProjectRole.ADMIN_PROJECT).subscribe((value) => {
      updatedUser = value;
    });

    expect(httpClient.patch).toHaveBeenCalledWith('/projects/project-1/users/member-1', {
      role: ProjectRole.ADMIN_PROJECT
    });
    expect(updatedUser?.projectRole).toBe(ProjectRole.ADMIN_PROJECT);
    expect(state.users.find((user) => user.id === 'member-1')?.projectRole).toBe(
      ProjectRole.ADMIN_PROJECT
    );
  });

  it('removes a project member from the local state', () => {
    state = {
      ...state,
      users: [
        ...state.users,
        createUser('member-1', 'Existing Member', 'member@example.com', ProjectRole.USER)
      ]
    };
    httpClient.delete.and.returnValue(of(void 0));

    service.removeProjectUser('member-1').subscribe();

    expect(httpClient.delete).toHaveBeenCalledWith('/projects/project-1/users/member-1');
    expect(state.users.some((user) => user.id === 'member-1')).toBeFalse();
  });

  it('updates onboarding mode in the local state', () => {
    httpClient.patch.and.returnValue(
      of({
        preferences: {
          new_employee_mode: true
        }
      })
    );

    let result: boolean | undefined;
    service.updateOnboardingPreferences(true).subscribe((value) => {
      result = value;
    });

    expect(httpClient.patch).toHaveBeenCalledWith('/projects/project-1/me/preferences', {
      new_employee_mode: true
    });
    expect(result).toBeTrue();
    expect(state.newEmployeeMode).toBeTrue();
  });

  it('deletes an issue through API and removes it from the local state', () => {
    state = {
      ...state,
      issues: [
        {
          id: 'issue-1',
          key: 'PRJ-1',
          title: 'Issue',
          type: 'task' as any,
          statusId: 'status-1',
          priority: 'Medium' as any,
          listPosition: 1,
          description: '',
          createdAt: '',
          updatedAt: '',
          reporterId: 'current-user',
          authorId: 'current-user',
          userIds: [],
          comments: [],
          projectId: 'project-1'
        }
      ]
    };
    httpClient.delete.and.returnValue(of(void 0));

    service.deleteIssue('issue-1').subscribe();

    expect(httpClient.delete).toHaveBeenCalledWith('/issues/issue-1');
    expect(state.issues).toEqual([]);
  });

  it('deletes the current project and resets project state', () => {
    httpClient.delete.and.returnValue(of(void 0));

    service.deleteProject('project-1').subscribe();

    expect(httpClient.delete).toHaveBeenCalledWith('/projects/project-1');
    expect(state.id).toBe('');
    expect(service.currentProjectId).toBeNull();
  });
});
