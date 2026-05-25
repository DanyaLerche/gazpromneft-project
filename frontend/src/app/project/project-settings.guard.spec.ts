import { of } from 'rxjs';
import { ProjectRole } from '@trungk18/interface/role';
import { ProjectSettingsGuard } from './project-settings.guard';

describe('ProjectSettingsGuard', () => {
  function createRoute(projectId: string | null = 'project-1'): any {
    return {
      pathFromRoot: [
        {
          paramMap: {
            get: (key: string) => (key === 'projectId' ? projectId : null)
          }
        }
      ]
    };
  }

  function setup(role: ProjectRole) {
    const projectQuery: any = {
      project$: of({ id: 'project-1', currentUserRole: role }),
      isLoading$: of(false),
      error$: of(null)
    };
    const projectService: any = {
      loadProjectIfNeeded: jasmine.createSpy('loadProjectIfNeeded')
    };
    const router: any = {
      createUrlTree: jasmine
        .createSpy('createUrlTree')
        .and.callFake((commands: string[]) => ({ commands }))
    };

    return {
      guard: new ProjectSettingsGuard(projectQuery, projectService, router),
      projectService,
      router
    };
  }

  it('should allow a project admin to open settings', async () => {
    const { guard, projectService } = setup(ProjectRole.ADMIN_PROJECT);

    const result = await guard.canActivate(createRoute()).toPromise();

    expect(projectService.loadProjectIfNeeded).toHaveBeenCalledWith('project-1');
    expect(result).toBeTrue();
  });

  it('should redirect a regular member to the board', async () => {
    const { guard, router } = setup(ProjectRole.USER);

    const result = await guard.canActivate(createRoute()).toPromise();

    expect(router.createUrlTree).toHaveBeenCalledWith(['/projects', 'project-1', 'board']);
    expect(result as any).toEqual({ commands: ['/projects', 'project-1', 'board'] });
  });

  it('should redirect to the projects page when project id is missing', async () => {
    const { guard, projectService, router } = setup(ProjectRole.ADMIN_PROJECT);

    const result = await guard.canActivate(createRoute(null)).toPromise();

    expect(projectService.loadProjectIfNeeded).not.toHaveBeenCalled();
    expect(router.createUrlTree).toHaveBeenCalledWith(['/projects']);
    expect(result as any).toEqual({ commands: ['/projects'] });
  });
});
