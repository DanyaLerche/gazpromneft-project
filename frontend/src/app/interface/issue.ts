import { JComment } from './comment';
import { StatusCategory } from './status';

/* eslint-disable no-shadow */
export enum IssueType {
  EPIC = 'epic',
  TASK = 'task',
  STORY = 'story',
  BUG = 'bug'
}

export enum IssueStatus {
  ЗАДЕРЖКА = 'Задержка',
  SELECTED = 'Selected',
  // eslint-disable-next-line @typescript-eslint/naming-convention
  IN_PROGRESS = 'InProgress',
  ВЫПОЛНЕНО = 'Выполнено'
}

export const IssueStatusDisplay = {
  [IssueStatus.ЗАДЕРЖКА]: 'Задержка',
  [IssueStatus.SELECTED]: 'Выбрано для разработки',
  [IssueStatus.IN_PROGRESS]: 'В процессе',
  [IssueStatus.ВЫПОЛНЕНО]: 'Выполнено'
};

export enum IssuePriority {
  LOWEST = 'Lowest',
  LOW = 'Low',
  MEDIUM = 'Medium',
  HIGH = 'High',
  HIGHEST = 'Highest'
}

export const IssuePriorityColors = {
  [IssuePriority.HIGHEST]: '#CD1317',
  [IssuePriority.HIGH]: '#E9494A',
  [IssuePriority.MEDIUM]: '#E97F33',
  [IssuePriority.LOW]: '#2D8738',
  [IssuePriority.LOWEST]: '#57A55A'
};
export interface JIssue {
  id: string;
  key: string;
  title: string;
  type: IssueType;
  status?: IssueStatus | string;
  statusId: string;
  statusName?: string;
  statusCategory?: StatusCategory;
  priority: IssuePriority;
  criticalityId?: string | null;
  criticalityName?: string | null;
  criticalityLevel?: number | null;
  listPosition: number;
  description: string;
  estimate?: number | null;
  timeSpent?: number | null;
  timeRemaining?: number | null;
  createdAt: string;
  updatedAt: string;
  reporterId: string;
  authorId: string;
  assigneeId?: string | null;
  userIds: string[];
  comments: JComment[];
  projectId: string;
  parentId?: string | null;
  startDate?: string | null;
  dueDate?: string | null;
  takenInWorkAt?: string | null;
  resolvedAt?: string | null;
}
/* eslint-enable no-shadow */
