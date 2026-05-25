export type StatusCategory = 'todo' | 'in_progress' | 'done';

export interface JStatus {
  id: string;
  projectId: string;
  name: string;
  category: StatusCategory;
  sortOrder: number;
}
