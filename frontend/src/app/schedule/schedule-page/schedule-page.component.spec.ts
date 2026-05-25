import { CommonModule } from '@angular/common';
import { NO_ERRORS_SCHEMA } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { RouterTestingModule } from '@angular/router/testing';
import { of } from 'rxjs';
import { NzNotificationService } from 'ng-zorro-antd/notification';
import { JSchedule } from '@trungk18/interface/schedule';
import { AuthQuery } from '@trungk18/project/auth/auth.query';
import { AuthService } from '@trungk18/project/auth/auth.service';
import { JWorklog, ScheduleService } from '@trungk18/schedule/schedule.service';
import { SchedulePageComponent } from './schedule-page.component';

describe('SchedulePageComponent', () => {
  let component: SchedulePageComponent;
  let fixture: ComponentFixture<SchedulePageComponent>;
  let authService: jasmine.SpyObj<AuthService>;
  let scheduleService: jasmine.SpyObj<ScheduleService>;

  const existingSchedule: JSchedule = {
    id: 'schedule-1',
    userId: 'user-1',
    date: '2026-03-27',
    plannedHours: 2,
    comment: 'Дежурство',
    createdAt: '2026-03-01T10:00:00Z',
    updatedAt: '2026-03-01T10:00:00Z'
  };
  const existingWorklog: JWorklog = {
    id: 'worklog-1',
    issueId: 'issue-1',
    userId: 'user-1',
    workDate: '2026-03-27',
    hours: 1.5,
    comment: 'Факт'
  };

  beforeEach(() => {
    window.localStorage.clear();

    scheduleService = jasmine.createSpyObj<ScheduleService>('ScheduleService', [
      'listUserSchedules',
      'listUserWorklogs',
      'listWorklogIssueOptions',
      'createIssueWorklog',
      'updateWorklog',
      'deleteWorklog',
      'createSchedule',
      'updateSchedule',
      'deleteSchedule'
    ]);
    scheduleService.listUserSchedules.and.returnValue(of([]));
    scheduleService.listUserWorklogs.and.returnValue(of([]));
    scheduleService.listWorklogIssueOptions.and.returnValue(
      of([{ id: 'issue-1', key: 'PAY-1', title: 'Issue one', label: 'PAY-1 — Issue one' }])
    );
    scheduleService.createIssueWorklog.and.returnValue(of(existingWorklog));
    scheduleService.updateWorklog.and.returnValue(of(existingWorklog));
    scheduleService.deleteWorklog.and.returnValue(of(void 0));
    scheduleService.createSchedule.and.returnValue(of(existingSchedule));
    scheduleService.updateSchedule.and.returnValue(of(existingSchedule));
    scheduleService.deleteSchedule.and.returnValue(of(void 0));
    authService = jasmine.createSpyObj<AuthService>('AuthService', ['logout']);
    authService.logout.and.returnValue(of(void 0));

    TestBed.configureTestingModule({
      declarations: [SchedulePageComponent],
      imports: [CommonModule, ReactiveFormsModule, RouterTestingModule],
      schemas: [NO_ERRORS_SCHEMA],
      providers: [
        {
          provide: AuthQuery,
          useValue: {
            userId$: of('user-1'),
            user$: of({ id: 'user-1', name: 'Alice Johnson', email: 'alice@example.com' })
          }
        },
        {
          provide: ScheduleService,
          useValue: scheduleService
        },
        {
          provide: AuthService,
          useValue: authService
        },
        {
          provide: NzNotificationService,
          useValue: {
            error: jasmine.createSpy('error')
          }
        }
      ]
    });

    fixture = TestBed.createComponent(SchedulePageComponent);
    component = fixture.componentInstance;
    component.focusedDate = new Date(2026, 2, 27);
    component.sidebarMonth = new Date(2026, 2, 1);
    (component as any).rebuildView();
  });

  it('loads schedules for the visible week on init', () => {
    scheduleService.listUserSchedules.and.returnValue(of([existingSchedule]));
    scheduleService.listUserWorklogs.and.returnValue(of([existingWorklog]));

    fixture.detectChanges();

    expect(scheduleService.listUserSchedules).toHaveBeenCalledWith(
      'user-1',
      '2026-03-23',
      '2026-03-29'
    );
    expect(component.plannerDays.length).toBe(7);
    expect(component.totalSchedules).toBe(1);
    expect(component.totalPlannedHours).toBe(2);
    expect(component.totalActualHours).toBe(1.5);
  });

  it('prefills the modal form for an existing derived task', () => {
    scheduleService.listUserSchedules.and.returnValue(of([existingSchedule]));
    scheduleService.listUserWorklogs.and.returnValue(of([existingWorklog]));

    fixture.detectChanges();

    const plannerDay = component.plannerDays.find((day) => day.iso === existingSchedule.date);
    expect(plannerDay?.plannedEvents.length).toBe(1);

    component.openExistingEvent(
      new MouseEvent('click'),
      plannerDay!,
      plannerDay!.plannedEvents[0].task
    );

    expect(component.showEditor).toBeTrue();
    expect(component.editorForm.getRawValue()).toEqual({
      startTime: '09:00',
      plannedHours: 2,
      actualIssueId: null,
      actualHours: 0,
      color: component.defaultTaskColor,
      comment: 'Дежурство'
    });
  });

  it('adds a second task to the same day and syncs only the daily aggregate to backend', () => {
    const updatedAggregate: JSchedule = {
      ...existingSchedule,
      plannedHours: 5,
      comment: '2 задач: Дежурство; Ревью'
    };

    scheduleService.listUserSchedules.and.returnValues(
      of([existingSchedule]),
      of([updatedAggregate])
    );
    scheduleService.listUserWorklogs.and.returnValues(of([]), of([]));
    scheduleService.updateSchedule.and.returnValue(of(updatedAggregate));

    fixture.detectChanges();

    component.openFocusedDate();
    component.editorForm.patchValue({
      startTime: '13:00',
      plannedHours: 3,
      color: '#0284c7',
      comment: '  Ревью  '
    });

    component.save();

    expect(scheduleService.updateSchedule).toHaveBeenCalledWith('schedule-1', {
      plannedHours: 5,
      comment: '2 задач: Дежурство; Ревью'
    });

    const plannerDay = component.plannerDays.find((day) => day.iso === existingSchedule.date);
    expect(plannerDay?.tasks.length).toBe(2);
    expect(plannerDay?.summaryLabel).toBe('5 ч • 2 задач');
  });

  it('persists color and time locally without backend update when daily aggregate is unchanged', () => {
    scheduleService.listUserSchedules.and.returnValue(of([existingSchedule]));
    scheduleService.listUserWorklogs.and.returnValue(of([]));

    fixture.detectChanges();

    const plannerDay = component.plannerDays.find((day) => day.iso === existingSchedule.date);
    component.openExistingEvent(
      new MouseEvent('click'),
      plannerDay!,
      plannerDay!.plannedEvents[0].task
    );
    component.editorForm.patchValue({
      startTime: '10:30',
      plannedHours: 2,
      color: '#db2777',
      comment: 'Дежурство'
    });

    component.save();

    expect(scheduleService.updateSchedule).not.toHaveBeenCalled();

    const storedTasks = JSON.parse(
      window.localStorage.getItem('schedule-day-tasks:user-1') ?? '[]'
    );
    expect(storedTasks).toEqual([
      jasmine.objectContaining({
        date: '2026-03-27',
        startTime: '10:30',
        plannedHours: 2,
        color: '#db2777',
        comment: 'Дежурство'
      })
    ]);
  });

  it('blocks saving when planned hours exceed the remaining workday', () => {
    fixture.detectChanges();

    component.openFocusedDate();
    component.editorForm.patchValue({
      startTime: '18:30',
      plannedHours: 2,
      color: '#4f46e5',
      comment: 'Поздняя задача'
    });
    component.editorForm.get('plannedHours')?.updateValueAndValidity();

    component.save();

    expect(component.editorForm.get('plannedHours')?.hasError('exceedsWorkday')).toBeTrue();
    expect(scheduleService.createSchedule).not.toHaveBeenCalled();
    expect(scheduleService.updateSchedule).not.toHaveBeenCalled();
  });

  it('deletes the last task on a day through the existing backend record', () => {
    spyOn(window, 'confirm').and.returnValue(true);
    scheduleService.listUserSchedules.and.returnValues(of([existingSchedule]), of([]));
    scheduleService.listUserWorklogs.and.returnValues(of([]), of([]));

    fixture.detectChanges();

    const plannerDay = component.plannerDays.find((day) => day.iso === existingSchedule.date);
    component.openExistingEvent(
      new MouseEvent('click'),
      plannerDay!,
      plannerDay!.plannedEvents[0].task
    );
    component.confirmDelete();

    expect(scheduleService.deleteSchedule).toHaveBeenCalledWith('schedule-1');
    expect(component.showEditor).toBeFalse();
  });

  it('creates worklog when actual issue and hours provided', () => {
    scheduleService.listUserSchedules.and.returnValues(of([]), of([]));
    scheduleService.listUserWorklogs.and.returnValues(of([]), of([existingWorklog]));

    fixture.detectChanges();

    component.openFocusedDate();
    component.editorForm.patchValue({
      startTime: '09:00',
      plannedHours: 0,
      actualIssueId: 'issue-1',
      actualHours: 2.5,
      color: '#4f46e5',
      comment: 'Факт по задаче'
    });

    component.save();

    expect(scheduleService.createIssueWorklog).toHaveBeenCalledWith('issue-1', {
      workDate: '2026-03-27',
      hours: 2.5,
      comment: 'Факт по задаче'
    });
  });
});
