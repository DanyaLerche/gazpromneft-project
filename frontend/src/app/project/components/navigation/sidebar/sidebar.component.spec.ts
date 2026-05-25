import { of } from 'rxjs';
import { ProjectRole } from '@trungk18/interface/role';
import { SidebarComponent } from './sidebar.component';

describe('SidebarComponent', () => {
  function createComponent(
    role: ProjectRole,
    currentUserId = 'user-1',
    onboardingAssigneeIds: string[] = []
  ) {
    const projectQuery: any = {
      all$: of({
        id: 'project-1',
        currentUserRole: role,
        onboardingAssigneeIds
      })
    };
    const authQuery: any = {
      getValue: () => ({ user: { id: currentUserId } })
    };
    const router: any = {
      createUrlTree: (commands: string[], extras?: any) => ({ commands, extras }),
      isActive: () => false
    };

    const component = new SidebarComponent(projectQuery, authQuery, router);
    component.ngOnInit();
    return component;
  }

  it('should show the settings link for a project admin', () => {
    const component = createComponent(ProjectRole.ADMIN_PROJECT);
    const settings = component.visibleSideBarLinks.find((link) => link.url === 'settings');
    const onboarding = component.visibleSideBarLinks.find((link) => link.url === 'onboarding');

    expect(settings?.disabled).toBeFalse();
    expect(onboarding?.disabled).toBeFalse();
  });

  it('should disable protected links for a regular project member', () => {
    const component = createComponent(ProjectRole.USER);
    const settings = component.visibleSideBarLinks.find((link) => link.url === 'settings');

    expect(settings?.disabled).toBeTrue();
  });

  it('should show the onboarding link when user is assigned by project admin', () => {
    const component = createComponent(ProjectRole.USER, 'assigned-user', ['assigned-user']);
    const onboarding = component.visibleSideBarLinks.find((link) => link.url === 'onboarding');

    expect(onboarding?.disabled).toBeFalse();
  });
});
