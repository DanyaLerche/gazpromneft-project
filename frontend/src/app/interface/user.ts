import { AppRole, ProjectRole } from './role';

export interface JUser {
  id: string;
  name: string;
  email: string;
  avatarUrl?: string;
  createdAt?: string;
  updatedAt?: string;
  issueIds?: string[];
  isActive?: boolean;
  appRole?: AppRole;
  projectRole?: ProjectRole;
}
