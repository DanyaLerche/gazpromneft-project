import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { JSchedule } from '@trungk18/interface/schedule';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { environment } from 'src/environments/environment';

interface ApiSchedule {
  id: string;
  user_id: string;
  date: string;
  planned_hours: number | null;
  comment: string | null;
  created_at: string | null;
  updated_at: string | null;
}

interface ApiPagedSchedules {
  items: ApiSchedule[];
  total: number;
}

interface ApiScheduleResponse {
  schedule: ApiSchedule;
}

interface ApiWorklog {
  id: string;
  issue_id: string;
  user_id: string;
  work_date: string;
  hours: number;
  comment: string | null;
}

interface ApiPagedWorklogs {
  items: ApiWorklog[];
  total: number;
}

interface ApiWorklogResponse {
  worklog: ApiWorklog;
}

interface ApiForMeIssue {
  id: string;
  key: string;
  title: string;
}

interface ApiForMeResponse {
  issues: ApiForMeIssue[];
}

export interface CreateSchedulePayload {
  date: string;
  plannedHours: number;
  comment: string | null;
}

export interface UpdateSchedulePayload {
  plannedHours?: number;
  comment?: string | null;
}

export interface JWorklog {
  id: string;
  issueId: string;
  userId: string;
  workDate: string;
  hours: number;
  comment: string | null;
}

export interface WorklogIssueOption {
  id: string;
  key: string;
  title: string;
  label: string;
}

export interface CreateWorklogPayload {
  workDate: string;
  hours: number;
  comment: string | null;
}

export interface UpdateWorklogPayload {
  workDate?: string;
  hours?: number;
  comment?: string | null;
}

@Injectable({
  providedIn: 'root'
})
export class ScheduleService {
  private readonly baseUrl = environment.apiUrl;

  constructor(private _http: HttpClient) {}

  listUserSchedules(userId: string, from: string, to: string): Observable<JSchedule[]> {
    const params = new HttpParams()
      .set('from', from)
      .set('to', to)
      .set('limit', '200')
      .set('offset', '0');

    return this._http
      .get<ApiPagedSchedules>(`${this.baseUrl}/users/${userId}/schedules`, { params })
      .pipe(map((response) => response.items.map((schedule) => this.mapSchedule(schedule))));
  }

  listUserWorklogs(userId: string, from: string, to: string): Observable<JWorklog[]> {
    const params = new HttpParams()
      .set('from', from)
      .set('to', to)
      .set('limit', '200')
      .set('offset', '0');

    return this._http
      .get<ApiPagedWorklogs>(`${this.baseUrl}/users/${userId}/worklogs`, { params })
      .pipe(map((response) => response.items.map((worklog) => this.mapWorklog(worklog))));
  }

  listWorklogIssueOptions(limit = 200): Observable<WorklogIssueOption[]> {
    const params = new HttpParams()
      .set('limit', String(limit))
      .set('offset', '0')
      .set('sort', 'updated_at');

    return this._http.get<ApiForMeResponse>(`${this.baseUrl}/for-me`, { params }).pipe(
      map((response) => {
        const uniqueIssues = new Map<string, WorklogIssueOption>();
        response.issues.forEach((issue) => {
          if (!issue?.id || uniqueIssues.has(issue.id)) {
            return;
          }

          const normalizedTitle = String(issue.title ?? '').trim();
          const normalizedKey = String(issue.key ?? '').trim();
          const displayTitle = normalizedTitle || normalizedKey || 'Без названия';
          const displayLabel = normalizedKey
            ? `${normalizedKey} — ${displayTitle}`
            : displayTitle;
          uniqueIssues.set(issue.id, {
            id: issue.id,
            key: normalizedKey,
            title: displayTitle,
            label: displayLabel
          });
        });

        return Array.from(uniqueIssues.values()).sort((left, right) =>
          left.label.localeCompare(right.label, 'ru')
        );
      })
    );
  }

  createSchedule(userId: string, payload: CreateSchedulePayload): Observable<JSchedule> {
    return this._http
      .post<ApiScheduleResponse>(`${this.baseUrl}/users/${userId}/schedules`, {
        date: payload.date,
        planned_hours: payload.plannedHours,
        comment: this.normalizeComment(payload.comment)
      })
      .pipe(map(({ schedule }) => this.mapSchedule(schedule)));
  }

  createIssueWorklog(issueId: string, payload: CreateWorklogPayload): Observable<JWorklog> {
    return this._http
      .post<ApiWorklogResponse>(`${this.baseUrl}/issues/${issueId}/worklogs`, {
        work_date: payload.workDate,
        hours: payload.hours,
        comment: this.normalizeComment(payload.comment)
      })
      .pipe(map(({ worklog }) => this.mapWorklog(worklog)));
  }

  updateSchedule(scheduleId: string, payload: UpdateSchedulePayload): Observable<JSchedule> {
    const body: Record<string, number | string | null> = {};

    if (payload.plannedHours !== undefined) {
      body['planned_hours'] = payload.plannedHours;
    }

    if (payload.comment !== undefined) {
      body['comment'] = this.normalizeComment(payload.comment);
    }

    return this._http
      .patch<ApiScheduleResponse>(`${this.baseUrl}/schedules/${scheduleId}`, body)
      .pipe(map(({ schedule }) => this.mapSchedule(schedule)));
  }

  updateWorklog(worklogId: string, payload: UpdateWorklogPayload): Observable<JWorklog> {
    const body: Record<string, number | string | null> = {};

    if (payload.workDate !== undefined) {
      body['work_date'] = payload.workDate;
    }

    if (payload.hours !== undefined) {
      body['hours'] = payload.hours;
    }

    if (payload.comment !== undefined) {
      body['comment'] = this.normalizeComment(payload.comment);
    }

    return this._http
      .patch<ApiWorklogResponse>(`${this.baseUrl}/worklogs/${worklogId}`, body)
      .pipe(map(({ worklog }) => this.mapWorklog(worklog)));
  }

  deleteSchedule(scheduleId: string): Observable<void> {
    return this._http.delete<void>(`${this.baseUrl}/schedules/${scheduleId}`);
  }

  deleteWorklog(worklogId: string): Observable<void> {
    return this._http.delete<void>(`${this.baseUrl}/worklogs/${worklogId}`);
  }

  private mapSchedule(schedule: ApiSchedule): JSchedule {
    return {
      id: schedule.id,
      userId: schedule.user_id,
      date: schedule.date,
      plannedHours: schedule.planned_hours ?? 0,
      comment: this.normalizeComment(schedule.comment),
      createdAt: schedule.created_at,
      updatedAt: schedule.updated_at
    };
  }

  private mapWorklog(worklog: ApiWorklog): JWorklog {
    return {
      id: worklog.id,
      issueId: worklog.issue_id,
      userId: worklog.user_id,
      workDate: worklog.work_date,
      hours: worklog.hours ?? 0,
      comment: this.normalizeComment(worklog.comment)
    };
  }

  private normalizeComment(comment: string | null | undefined): string | null {
    const trimmedComment = comment?.trim() ?? '';
    return trimmedComment ? trimmedComment : null;
  }
}
