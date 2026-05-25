import { JCriticality } from './criticality';
import { JIssue } from './issue';
import { ProjectRole } from './role';
import { JStatus } from './status';
import { JUser } from './user';

export interface JProject {
  id: string;
  key: string;
  name: string;
  createdBy: string;
  createdAt: string;
  description: string;
  category: ProjectCategory;
  updateAt: string;
  currentUserRole: ProjectRole | null;
  newEmployeeMode: boolean;
  onboardingAssigneeIds: string[];
  issues: JIssue[];
  users: JUser[];
  statuses: JStatus[];
  criticalities: JCriticality[];
}

export interface JProjectSummary {
  id: string;
  key: string;
  name: string;
  createdBy: string;
  createdAt: string;
  currentUserRole: ProjectRole | null;
}

// eslint-disable-next-line no-shadow
export enum ProjectCategory {
  SOFTWARE = 'Software',
  MARKETING = 'Marketing',
  BUSINESS = 'Business'
}

export interface JTaskSummary {
  completed: number;
  inProgress: number;
  notStarted: number;
  total: number;
}

export interface JTaskByAssignee {
  assigneeId: string | null;
  assigneeName: string;
  completed: number;
  inProgress: number;
  notStarted: number;
  total: number;
}

export interface JEffortSummary {
  plannedHours: number;
  actualHours: number;
  varianceHours: number;
  actualVsPlanPercent: number | null;
}

export interface JEffortByAssignee {
  assigneeId: string | null;
  assigneeName: string;
  plannedHours: number;
  actualHours: number;
  varianceHours: number;
  actualVsPlanPercent: number | null;
}

export interface JStatusDistributionItem {
  statusId: string;
  statusName: string;
  statusCategory: string;
  tasksCount: number;
}

export interface JOverdueTask {
  issueId: string;
  issueKey: string;
  title: string;
  assigneeId: string | null;
  assigneeName: string;
  dueDate: string;
  statusName: string | null;
  daysOverdue: number;
}

export interface JOverdueByAssignee {
  assigneeId: string | null;
  assigneeName: string;
  tasksCount: number;
}

export interface JOverdueSection {
  totalOverdueTasks: number;
  overdueByAssignee: JOverdueByAssignee[];
  tasks: JOverdueTask[];
}

export interface JWorkloadItem {
  assigneeId: string | null;
  assigneeName: string;
  openTasks: number;
  plannedHoursOpenTasks: number;
}

export interface JRecentActivity {
  days: number;
  createdTasks: number;
  completedTasks: number;
  loggedHours: number;
  completionToCreationPercent: number | null;
}

export interface JProjectDashboardReport {
  projectId: string;
  generatedAt: string;
  taskSummary: JTaskSummary;
  tasksByAssignee: JTaskByAssignee[];
  effortSummary: JEffortSummary;
  effortByAssignee: JEffortByAssignee[];
  statusDistribution: JStatusDistributionItem[];
  overdue: JOverdueSection;
  workload: JWorkloadItem[];
  recentActivity: JRecentActivity;
}
