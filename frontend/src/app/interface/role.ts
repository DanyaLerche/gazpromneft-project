export enum AppRole {
  USER = 'user',
  ADMIN_APP = 'admin_app'
}

export enum ProjectRole {
  USER = 'user',
  ADMIN_PROJECT = 'admin_project'
}

export function isAdminAppRole(role?: AppRole | null): boolean {
  return role === AppRole.ADMIN_APP;
}

export function isAdminProjectRole(role?: ProjectRole | null): boolean {
  return role === ProjectRole.ADMIN_PROJECT;
}

export function getAppRoleLabel(role?: AppRole | null): string {
  switch (role) {
    case AppRole.ADMIN_APP:
      return 'Администратор платформы';
    default:
      return 'Участник платформы';
  }
}

export function getProjectRoleLabel(role?: ProjectRole | null): string {
  switch (role) {
    case ProjectRole.ADMIN_PROJECT:
      return 'Администратор проекта';
    default:
      return 'Участник проекта';
  }
}
