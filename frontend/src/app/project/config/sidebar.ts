import { SideBarLink } from '@trungk18/interface/ui-model/nav-link';

export const SideBarLinks = [
  new SideBarLink('Board', 'board', 'board'),
  new SideBarLink('Reports & Dashboards', 'report', 'reports', true),
  new SideBarLink('New Employee', 'star', 'onboarding', false, true),
  new SideBarLink('Documentation', 'page', 'documentation'),
  new SideBarLink('Project Settings', 'cog', 'settings', true)
];
