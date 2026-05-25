export interface JSchedule {
  id: string;
  userId: string;
  date: string;
  plannedHours: number;
  comment: string | null;
  createdAt: string | null;
  updatedAt: string | null;
}
