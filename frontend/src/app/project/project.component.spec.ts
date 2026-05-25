import { ProjectComponent } from '@trungk18/project/project.component';


describe('ProjectComponent', () => {
  let component: ProjectComponent;

  const projectService: any = {};
  const route: any = {};
  const router: any = { url: '/projects/1/board' };
  const projectQuery: any = {};
  const filterService: any = {};
  const filterQuery: any = {};
  const authService: any = {};
  const authQuery: any = {};

  beforeEach(() => {
    component = new ProjectComponent(
      projectService,
      route,
      router,
      projectQuery,
      filterService,
      filterQuery,
      authService,
      authQuery
    );
  });

  it('should be able to toggle', () => {
    component.expanded = false;
    component.manualToggle();
    expect(component.expanded).toBe(true);
  });
});
