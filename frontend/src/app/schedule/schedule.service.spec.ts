import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import {
  CreateSchedulePayload,
  ScheduleService,
  UpdateSchedulePayload
} from '@trungk18/schedule/schedule.service';
import { environment } from 'src/environments/environment';

describe('ScheduleService', () => {
  let service: ScheduleService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [ScheduleService]
    });

    service = TestBed.inject(ScheduleService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('loads user schedules for the visible period', () => {
    let actualSchedules: any[] = [];

    service
      .listUserSchedules('user-1', '2026-02-23', '2026-04-05')
      .subscribe((schedules) => {
        actualSchedules = schedules;
      });

    const request = httpMock.expectOne(
      `${environment.apiUrl}/users/user-1/schedules?from=2026-02-23&to=2026-04-05&limit=200&offset=0`
    );

    expect(request.request.method).toBe('GET');
    request.flush({
      items: [
        {
          id: 'schedule-1',
          user_id: 'user-1',
          date: '2026-03-27',
          planned_hours: 7.5,
          comment: 'Office',
          created_at: '2026-03-01T10:00:00Z',
          updated_at: '2026-03-02T10:00:00Z'
        }
      ],
      total: 1
    });

    expect(actualSchedules).toEqual([
      {
        id: 'schedule-1',
        userId: 'user-1',
        date: '2026-03-27',
        plannedHours: 7.5,
        comment: 'Office',
        createdAt: '2026-03-01T10:00:00Z',
        updatedAt: '2026-03-02T10:00:00Z'
      }
    ]);
  });

  it('creates a schedule and trims empty comment payload', () => {
    const payload: CreateSchedulePayload = {
      date: '2026-03-28',
      plannedHours: 8,
      comment: '  Работа в офисе  '
    };

    service.createSchedule('user-1', payload).subscribe();

    const request = httpMock.expectOne(`${environment.apiUrl}/users/user-1/schedules`);

    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({
      date: '2026-03-28',
      planned_hours: 8,
      comment: 'Работа в офисе'
    });

    request.flush({
      schedule: {
        id: 'schedule-2',
        user_id: 'user-1',
        date: '2026-03-28',
        planned_hours: 8,
        comment: 'Работа в офисе',
        created_at: '2026-03-01T10:00:00Z',
        updated_at: '2026-03-01T10:00:00Z'
      }
    });
  });

  it('updates only changed fields', () => {
    const payload: UpdateSchedulePayload = {
      comment: '  Удаленно  '
    };

    service.updateSchedule('schedule-1', payload).subscribe();

    const request = httpMock.expectOne(`${environment.apiUrl}/schedules/schedule-1`);

    expect(request.request.method).toBe('PATCH');
    expect(request.request.body).toEqual({
      comment: 'Удаленно'
    });

    request.flush({
      schedule: {
        id: 'schedule-1',
        user_id: 'user-1',
        date: '2026-03-27',
        planned_hours: 8,
        comment: 'Удаленно',
        created_at: '2026-03-01T10:00:00Z',
        updated_at: '2026-03-03T10:00:00Z'
      }
    });
  });

  it('deletes a schedule by id', () => {
    service.deleteSchedule('schedule-1').subscribe();

    const request = httpMock.expectOne(`${environment.apiUrl}/schedules/schedule-1`);
    expect(request.request.method).toBe('DELETE');
    request.flush(null);
  });

  it('loads user worklogs for selected period', () => {
    let actualWorklogs: any[] = [];

    service
      .listUserWorklogs('user-1', '2026-03-23', '2026-03-29')
      .subscribe((worklogs) => {
        actualWorklogs = worklogs;
      });

    const request = httpMock.expectOne(
      `${environment.apiUrl}/users/user-1/worklogs?from=2026-03-23&to=2026-03-29&limit=200&offset=0`
    );
    expect(request.request.method).toBe('GET');
    request.flush({
      items: [
        {
          id: 'worklog-1',
          issue_id: 'issue-1',
          user_id: 'user-1',
          work_date: '2026-03-27',
          hours: 3.5,
          comment: 'Факт'
        }
      ],
      total: 1
    });

    expect(actualWorklogs).toEqual([
      {
        id: 'worklog-1',
        issueId: 'issue-1',
        userId: 'user-1',
        workDate: '2026-03-27',
        hours: 3.5,
        comment: 'Факт'
      }
    ]);
  });

  it('creates issue worklog with normalized comment', () => {
    service
      .createIssueWorklog('issue-1', {
        workDate: '2026-03-27',
        hours: 2,
        comment: '  Выполнено  '
      })
      .subscribe();

    const request = httpMock.expectOne(`${environment.apiUrl}/issues/issue-1/worklogs`);
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({
      work_date: '2026-03-27',
      hours: 2,
      comment: 'Выполнено'
    });
    request.flush({
      worklog: {
        id: 'worklog-2',
        issue_id: 'issue-1',
        user_id: 'user-1',
        work_date: '2026-03-27',
        hours: 2,
        comment: 'Выполнено'
      }
    });
  });

  it('updates worklog fields', () => {
    service
      .updateWorklog('worklog-1', {
        workDate: '2026-03-28',
        hours: 1.5,
        comment: '  Обновлено  '
      })
      .subscribe();

    const request = httpMock.expectOne(`${environment.apiUrl}/worklogs/worklog-1`);
    expect(request.request.method).toBe('PATCH');
    expect(request.request.body).toEqual({
      work_date: '2026-03-28',
      hours: 1.5,
      comment: 'Обновлено'
    });
    request.flush({
      worklog: {
        id: 'worklog-1',
        issue_id: 'issue-1',
        user_id: 'user-1',
        work_date: '2026-03-28',
        hours: 1.5,
        comment: 'Обновлено'
      }
    });
  });

  it('deletes worklog by id', () => {
    service.deleteWorklog('worklog-1').subscribe();

    const request = httpMock.expectOne(`${environment.apiUrl}/worklogs/worklog-1`);
    expect(request.request.method).toBe('DELETE');
    request.flush(null);
  });

  it('builds worklog issue options without exposing internal issue uuid in labels', () => {
    let actualOptions: any[] = [];

    service.listWorklogIssueOptions().subscribe((options) => {
      actualOptions = options;
    });

    const request = httpMock.expectOne(
      `${environment.apiUrl}/for-me?limit=200&offset=0&sort=updated_at`
    );
    expect(request.request.method).toBe('GET');
    request.flush({
      issues: [
        {
          id: 'issue-1',
          key: 'PAY-1',
          title: 'Issue one'
        }
      ]
    });

    expect(actualOptions).toEqual([
      {
        id: 'issue-1',
        key: 'PAY-1',
        title: 'Issue one',
        label: 'PAY-1 — Issue one'
      }
    ]);
  });
});
