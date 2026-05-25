import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { Router } from '@angular/router';
import { UntilDestroy, untilDestroyed } from '@ngneat/until-destroy';
import { JProject } from '@trungk18/interface/project';
import { isAdminProjectRole } from '@trungk18/interface/role';
import { AuthQuery } from '@trungk18/project/auth/auth.query';
import { ProjectQuery } from '@trungk18/project/state/project/project.query';

type SidebarSection = 'workspace' | 'productivity' | 'management';

interface SidebarNavItem {
  key: string;
  name: string;
  icon: string;
  section: SidebarSection;
  url?: string;
  absoluteUrl?: string;
  queryParams?: Record<string, string>;
  requiresProjectAdmin?: boolean;
  requiresNewEmployeeMode?: boolean;
  disabled?: boolean;
}

@Component({
  selector: 'app-sidebar',
  templateUrl: './sidebar.component.html',
  styleUrls: ['./sidebar.component.scss']
})
@UntilDestroy()
export class SidebarComponent implements OnInit {
  @Input() expanded!: boolean;
  @Input() mobileOpen = false;
  @Output() toggleRequested = new EventEmitter<void>();

  get sidebarWidth(): number {
    return this.expanded ? 260 : 88;
  }

  project!: JProject;
  sideBarLinks: SidebarNavItem[] = [];
  readonly sections: { key: SidebarSection; title: string }[] = [
    { key: 'workspace', title: 'Рабочее пространство' },
    { key: 'productivity', title: 'Продуктивность' },
    { key: 'management', title: 'Управление' }
  ];

  constructor(
    private _projectQuery: ProjectQuery,
    private _authQuery: AuthQuery,
    private _router: Router
  ) {
    this._projectQuery.all$.pipe(untilDestroyed(this)).subscribe((project) => {
      this.project = project;
    });
  }

  ngOnInit(): void {
    this.sideBarLinks = [
      { key: 'board', name: 'Доска', icon: 'board', section: 'workspace', url: 'board' },
      { key: 'projects', name: 'Проекты', icon: 'component', section: 'workspace', absoluteUrl: '/projects' },
      { key: 'calendar', name: 'Календарь', icon: 'feedback', section: 'workspace', absoluteUrl: '/schedule' },
      { key: 'dashboards', name: 'Дашборды', icon: 'report', section: 'productivity', url: 'dashboards' },
      { key: 'documentation', name: 'Документы', icon: 'page', section: 'productivity', url: 'documentation' },
      {
        key: 'users',
        name: 'Пользователи',
        icon: 'star',
        section: 'management',
        url: 'onboarding',
        requiresNewEmployeeMode: true
      },
      {
        key: 'settings',
        name: 'Настройки',
        icon: 'cog',
        section: 'management',
        url: 'settings',
        requiresProjectAdmin: true
      }
    ];
  }

  get visibleSideBarLinks(): SidebarNavItem[] {
    return this.sideBarLinks.map((link) => ({
      ...link,
      disabled:
        !!link.disabled ||
        (link.requiresProjectAdmin && !isAdminProjectRole(this.project?.currentUserRole)) ||
        (link.requiresNewEmployeeMode && !this.canAccessOnboarding)
    }));
  }

  sectionLinks(section: SidebarSection): SidebarNavItem[] {
    return this.visibleSideBarLinks.filter((link) => link.section === section);
  }

  private get canAccessOnboarding(): boolean {
    if (isAdminProjectRole(this.project?.currentUserRole)) {
      return true;
    }

    const currentUserId = this._authQuery.getValue().user?.id;
    if (!currentUserId) {
      return false;
    }

    return (this.project?.onboardingAssigneeIds ?? []).includes(currentUserId);
  }

  getLink(link: SidebarNavItem): string[] {
    if (link.absoluteUrl) {
      return [link.absoluteUrl];
    }

    if (!this.project?.id || !link.url) {
      return ['/projects'];
    }

    return ['/projects', this.project.id, link.url];
  }

  isLinkActive(link: SidebarNavItem): boolean {
    const tree = this._router.createUrlTree(this.getLink(link), {
      queryParams: link.queryParams
    });

    return this._router.isActive(tree, {
      paths: 'exact',
      queryParams: 'exact',
      fragment: 'ignored',
      matrixParams: 'ignored'
    });
  }

  trackByName = (_index: number, link: SidebarNavItem) => link.name;
}
