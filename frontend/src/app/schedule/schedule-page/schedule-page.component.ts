import { Component, HostListener, OnInit } from '@angular/core';
import {
  AbstractControl,
  UntypedFormBuilder,
  UntypedFormGroup,
  ValidationErrors,
  Validators
} from '@angular/forms';
import { UntilDestroy, untilDestroyed } from '@ngneat/until-destroy';
import { getApiErrorMessage } from '@trungk18/core/utils/api-error';
import { getAppRoleLabel } from '@trungk18/interface/role';
import { JSchedule } from '@trungk18/interface/schedule';
import { AuthQuery } from '@trungk18/project/auth/auth.query';
import { AuthService } from '@trungk18/project/auth/auth.service';
import {
  JWorklog,
  ScheduleService,
  UpdateSchedulePayload,
  WorklogIssueOption
} from '@trungk18/schedule/schedule.service';
import {
  addMonths,
  addWeeks,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isSameMonth,
  isSameWeek,
  isToday,
  startOfMonth,
  startOfWeek
} from 'date-fns';
import { ru } from 'date-fns/locale';
import { NzNotificationService } from 'ng-zorro-antd/notification';
import { Observable, forkJoin, of } from 'rxjs';
import { distinctUntilChanged, filter, finalize, map, switchMap } from 'rxjs/operators';

type ScheduleTaskSource = 'derived' | 'local';

type ScheduleTask = {
  id: string;
  date: string;
  startTime: string;
  plannedHours: number;
  color: string;
  comment: string | null;
  actualWorklogId: string | null;
  actualIssueId: string | null;
  actualHours: number | null;
  source: ScheduleTaskSource;
};

type PlannerEvent = {
  task: ScheduleTask;
  title: string;
  timeLabel: string;
  style: Record<string, string>;
};

type ActualPlannerEvent = {
  id: string;
  issueTitle: string;
  issueId: string;
  title: string;
  timeLabel: string;
  hoursLabel: string;
  hours: number;
  style: Record<string, string>;
};

type PlannerDay = {
  date: Date;
  iso: string;
  dayNumber: number;
  weekdayLabel: string;
  fullLabel: string;
  isToday: boolean;
  isWeekend: boolean;
  isFocused: boolean;
  tasks: ScheduleTask[];
  plannedEvents: PlannerEvent[];
  actualEvents: ActualPlannerEvent[];
  hasSchedules: boolean;
  totalPlannedHours: number;
  totalActualHours: number;
  summaryLabel: string;
};

type MiniCalendarDay = {
  date: Date;
  iso: string;
  dayNumber: number;
  isCurrentMonth: boolean;
  isToday: boolean;
  isFocused: boolean;
  isInFocusedWeek: boolean;
  hasSchedule: boolean;
};

@Component({
  templateUrl: './schedule-page.component.html',
  styleUrls: ['./schedule-page.component.scss']
})
@UntilDestroy()
export class SchedulePageComponent implements OnInit {
  readonly weekDayLabels = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
  readonly profileRole = 'Участник платформы';
  readonly profileTeam = 'Личный календарь';
  readonly profileInfo =
    'Планирует собственные задачи и рабочие смены в личном календаре.';
  readonly plannerStartHour = 8;
  readonly plannerEndHour = 20;
  readonly plannerMinuteStep = 30;
  readonly defaultShiftStartHour = 9;
  readonly defaultTaskColor = '#6C4CF1';
  readonly actualTaskColor = '#3B82F6';
  readonly plannerRowHeight = 72;
  readonly taskColorOptions = [
    { label: 'Фиолетовый', value: '#6C4CF1' },
    { label: 'Лавандовый', value: '#8B5CF6' },
    { label: 'Индиго', value: '#4F46E5' },
    { label: 'Синий', value: '#3B82F6' },
    { label: 'Бирюзовый', value: '#14B8A6' },
    { label: 'Зелёный', value: '#22C55E' },
    { label: 'Янтарный', value: '#F59E0B' },
    { label: 'Оранжевый', value: '#F97316' },
    { label: 'Красный', value: '#EF4444' },
    { label: 'Розовый', value: '#EC4899' },
    { label: 'Серый', value: '#64748B' }
  ];
  readonly timeSlots = Array.from(
    { length: this.plannerEndHour - this.plannerStartHour },
    (_unused, index) => this.plannerStartHour + index
  );
  readonly timezoneLabel = this.buildTimezoneLabel();

  editorForm: UntypedFormGroup;
  errorMessage = '';
  focusedDate = this.stripTime(new Date());
  isDeleting = false;
  isLoading = false;
  isLoggingOut = false;
  isSaving = false;
  isLoadingIssueOptions = false;
  miniCalendarDays: MiniCalendarDay[] = [];
  modalErrorMessage = '';
  plannerDays: PlannerDay[] = [];
  worklogIssueOptions: WorklogIssueOption[] = [];
  selectedDate: string | null = null;
  selectedTask: ScheduleTask | null = null;
  showEditor = false;
  showColorDropdown = false;
  sidebarMonth = startOfMonth(this.focusedDate);
  totalActualHours = 0;
  totalPlannedHours = 0;
  totalSchedules = 0;
  visiblePeriodLabel = '';
  weekLabel = '';
  currentTimeIndicator: { dayIso: string; top: string } | null = null;

  private readonly hoursFormatter = new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 1
  });
  private localTasksByDate = new Map<string, ScheduleTask[]>();
  private serverRecordsByDate = new Map<string, JSchedule>();
  private serverWorklogsByDate = new Map<string, JWorklog[]>();
  private worklogIssueOptionsById = new Map<string, WorklogIssueOption>();
  private userId: string | null = null;

  constructor(
    public authQuery: AuthQuery,
    private _fb: UntypedFormBuilder,
    private _authService: AuthService,
    private _notification: NzNotificationService,
    private _scheduleService: ScheduleService
  ) {
    this.editorForm = this._fb.group({
      startTime: [
        this.formatMinutesValue(this.getDefaultStartMinutes()),
        [Validators.required, this.validateStartTime.bind(this)]
      ],
      plannedHours: [
        0,
        [Validators.required, Validators.min(0), this.validatePlannedHours.bind(this)]
      ],
      actualIssueId: [null as string | null],
      actualHours: [0, [Validators.min(0)]],
      color: [this.defaultTaskColor, [Validators.required]],
      comment: ['', [Validators.maxLength(1000)]]
    });

    this.editorForm
      .get('startTime')
      ?.valueChanges.pipe(untilDestroyed(this))
      .subscribe(() => {
        this.editorForm.get('plannedHours')?.updateValueAndValidity({ emitEvent: false });
      });

    this.rebuildView();
  }

  ngOnInit(): void {
    this.authQuery.userId$
      .pipe(
        filter((userId): userId is string => !!userId),
        distinctUntilChanged(),
        untilDestroyed(this)
      )
      .subscribe((userId) => {
        this.userId = userId;
        this.loadLocalTasks();
        this.loadCurrentPeriod();
      });
  }

  get currentProfileRole(): string {
    return getAppRoleLabel(this.authQuery.getValue().user?.appRole);
  }

  @HostListener('document:keydown.escape')
  handleEscape(): void {
    if (this.showColorDropdown) {
      this.showColorDropdown = false;
      return;
    }

    if (this.showEditor) {
      this.closeEditor();
    }
  }

  @HostListener('document:mousedown', ['$event'])
  handleDocumentMousedown(event: MouseEvent): void {
    if (!this.showColorDropdown) {
      return;
    }

    const target = event.target as HTMLElement | null;

    if (!target?.closest('.schedule-color-picker')) {
      this.showColorDropdown = false;
    }
  }

  get monthLabel(): string {
    return this.capitalize(format(this.sidebarMonth, 'LLLL yyyy', { locale: ru }));
  }

  get focusedDateLabel(): string {
    return this.capitalize(format(this.focusedDate, 'EEEE, d MMMM', { locale: ru }));
  }

  get selectedDateLabel(): string {
    if (!this.selectedDate) {
      return '';
    }

    return this.capitalize(
      format(this.parseIsoDate(this.selectedDate), 'EEEE, d MMMM yyyy', { locale: ru })
    );
  }

  get plannedHoursControlInvalid(): boolean {
    const control = this.editorForm.get('plannedHours');
    return !!control && control.invalid && (control.dirty || control.touched);
  }

  get startTimeControlInvalid(): boolean {
    const control = this.editorForm.get('startTime');
    return !!control && control.invalid && (control.dirty || control.touched);
  }

  get selectedMaxPlannedHours(): number {
    const startMinutes = this.parseTimeInput(this.editorForm.get('startTime')?.value);
    if (startMinutes === null) {
      return 0;
    }

    return this.getMaxPlannedHoursForStartMinutes(startMinutes);
  }

  get plannedHoursErrorMessage(): string {
    const control = this.editorForm.get('plannedHours');

    if (control?.hasError('required')) {
      return 'Укажите количество часов.';
    }

    if (control?.hasError('min')) {
      return 'Укажите число не меньше 0.';
    }

    return `Для этого времени доступно максимум ${this.formatHours(this.selectedMaxPlannedHours)}.`;
  }

  get selectedTaskColor(): string {
    return this.normalizeColor(this.editorForm.get('color')?.value) ?? this.defaultTaskColor;
  }

  previousWeek(): void {
    this.setFocusedDate(addWeeks(this.focusedDate, -1), true);
  }

  nextWeek(): void {
    this.setFocusedDate(addWeeks(this.focusedDate, 1), true);
  }

  previousMonth(): void {
    this.setFocusedDate(addMonths(this.focusedDate, -1), true);
  }

  nextMonth(): void {
    this.setFocusedDate(addMonths(this.focusedDate, 1), true);
  }

  goToToday(): void {
    const today = this.stripTime(new Date());
    const shouldReload = !isSameWeek(today, this.focusedDate, { weekStartsOn: 1 });

    this.setFocusedDate(today, shouldReload);
  }

  retryLoad(): void {
    this.loadCurrentPeriod();
  }

  logout(): void {
    this.isLoggingOut = true;
    this._authService
      .logout()
      .pipe(
        finalize(() => {
          this.isLoggingOut = false;
        })
      )
      .subscribe();
  }

  getUserInitial(user: { name?: string | null; email?: string | null } | null): string {
    if (!user) {
      return '?';
    }

    return (user.name || user.email || '?').charAt(0).toUpperCase();
  }

  selectMiniCalendarDay(day: MiniCalendarDay): void {
    const shouldReload = !isSameWeek(day.date, this.focusedDate, { weekStartsOn: 1 });
    this.setFocusedDate(day.date, shouldReload);
  }

  openFocusedDate(): void {
    const iso = format(this.focusedDate, 'yyyy-MM-dd');
    this.openEditorForTask(iso, null, this.getSuggestedStartMinutesForDay(iso));
  }

  openCurrentMoment(): void {
    const now = new Date();
    const today = this.stripTime(now);
    const shouldReload = !isSameWeek(today, this.focusedDate, { weekStartsOn: 1 });

    this.setFocusedDate(today, shouldReload);
    this.openEditorForTask(format(today, 'yyyy-MM-dd'), null, this.getCurrentStartMinutes(now));
  }

  focusDay(day: PlannerDay): void {
    this.setFocusedDate(day.date, false);
  }

  createTaskAtPosition(event: MouseEvent, day: PlannerDay): void {
    this.setFocusedDate(day.date, false);
    this.openEditorForTask(day.iso, null, this.resolveStartMinutesFromPointer(event));
  }

  openExistingEvent(event: MouseEvent, day: PlannerDay, task: ScheduleTask): void {
    event.stopPropagation();
    this.setFocusedDate(day.date, false);
    this.openEditorForTask(day.iso, task, this.parseTimeInput(task.startTime) ?? this.getDefaultStartMinutes());
  }

  closeEditor(force = false): void {
    if (!force && (this.isSaving || this.isDeleting)) {
      return;
    }

    this.showEditor = false;
    this.showColorDropdown = false;
    this.selectedDate = null;
    this.selectedTask = null;
    this.modalErrorMessage = '';
    this.resetEditorForm(this.getDefaultStartMinutes());
  }

  onBackdropClick(event: MouseEvent): void {
    if (event.target === event.currentTarget) {
      this.closeEditor();
    }
  }

  onPlannerDayKeydown(event: KeyboardEvent, day: PlannerDay): void {
    if (event.key === 'Enter' || event.key === ' ' || event.key === 'Spacebar') {
      event.preventDefault();
      this.setFocusedDate(day.date, false);
      this.openEditorForTask(day.iso, null, this.getSuggestedStartMinutesForDay(day.iso));
    }
  }

  save(): void {
    if (this.isSaving || this.isDeleting || !this.userId || !this.selectedDate) {
      return;
    }

    if (this.editorForm.invalid) {
      this.editorForm.markAllAsTouched();
      return;
    }

    const startTime = this.normalizeTimeInput(this.editorForm.get('startTime')?.value);
    const plannedHours = Number(this.editorForm.get('plannedHours')?.value ?? 0);
    const actualIssueId = this.normalizeIssueId(this.editorForm.get('actualIssueId')?.value);
    const actualHours = this.normalizeHours(Number(this.editorForm.get('actualHours')?.value ?? 0));
    const color = this.normalizeColor(this.editorForm.get('color')?.value);
    const comment = this.normalizeComment(this.editorForm.get('comment')?.value);

    if (!startTime) {
      this.editorForm.get('startTime')?.setErrors({ invalidTime: true });
      return;
    }

    if (!color) {
      this.modalErrorMessage = 'Выберите цвет задачи.';
      return;
    }

    if (actualHours > 0 && !actualIssueId) {
      this.modalErrorMessage = 'Выберите задачу, чтобы списать фактические часы.';
      return;
    }

    const nextTask: ScheduleTask = {
      id: this.selectedTask?.id ?? this.generateTaskId(this.selectedDate),
      date: this.selectedDate,
      startTime,
      plannedHours,
      color,
      comment,
      actualWorklogId: this.selectedTask?.actualWorklogId ?? null,
      actualIssueId: actualHours > 0 ? (actualIssueId ?? null) : null,
      actualHours: actualHours > 0 ? actualHours : null,
      source: 'local'
    };
    const nextDayTasks = this.mergeTaskIntoDay(this.selectedDate, nextTask);
    const scheduleRequest$ = this.buildDayMutationRequest(this.selectedDate, nextDayTasks);
    const actualRequest$ = this.buildActualMutationRequest(
      this.selectedDate,
      nextTask,
      this.selectedTask
    );

    if (!scheduleRequest$ && !actualRequest$) {
      this.applyLocalTasksForDate(this.selectedDate, nextDayTasks);
      this.closeEditor(true);
      this.rebuildView();
      return;
    }

    const selectedDate = this.selectedDate;
    this.modalErrorMessage = '';
    this.isSaving = true;
    this.executePersistRequests(scheduleRequest$, actualRequest$)
      .pipe(
        finalize(() => {
          this.isSaving = false;
        })
      )
      .subscribe({
        next: (mutationResult) => {
          const persistedTask = this.applyActualMutationResult(nextTask, mutationResult.actualWorklog);
          const persistedDayTasks = nextDayTasks.map((task) =>
            task.id === persistedTask.id ? persistedTask : task
          );
          this.applyLocalTasksForDate(selectedDate, persistedDayTasks);
          this.closeEditor(true);
          this.loadCurrentPeriod();
        },
        error: (error) => {
          this.modalErrorMessage = this.getMutationErrorMessage(error);
          this._notification.error(
            error?.status === 409 ? 'Конфликт при сохранении' : 'Не удалось сохранить задачу',
            this.modalErrorMessage
          );
        }
      });
  }

  confirmDelete(): void {
    if (!this.selectedTask || !this.selectedDate || this.isSaving || this.isDeleting) {
      return;
    }

    const isConfirmed = window.confirm('Удалить выбранную задачу из календаря?');
    if (!isConfirmed) {
      return;
    }

    const nextDayTasks = this
      .getTasksForDate(this.selectedDate)
      .filter((task) => task.id !== this.selectedTask?.id);
    const scheduleRequest$ = this.buildDayMutationRequest(this.selectedDate, nextDayTasks);
    const deleteWorklogRequest$ = this.selectedTask.actualWorklogId
      ? this._scheduleService
          .deleteWorklog(this.selectedTask.actualWorklogId)
          .pipe(map(() => ({ actualWorklog: null as JWorklog | null })))
      : null;

    if (!scheduleRequest$ && !deleteWorklogRequest$) {
      this.applyLocalTasksForDate(this.selectedDate, nextDayTasks);
      this.closeEditor(true);
      this.rebuildView();
      return;
    }

    const selectedDate = this.selectedDate;
    this.modalErrorMessage = '';
    this.isDeleting = true;
    this.executePersistRequests(scheduleRequest$, deleteWorklogRequest$)
      .pipe(
        finalize(() => {
          this.isDeleting = false;
        })
      )
      .subscribe({
        next: () => {
          this.applyLocalTasksForDate(selectedDate, nextDayTasks);
          this.closeEditor(true);
          this.loadCurrentPeriod();
        },
        error: (error) => {
          this.modalErrorMessage = this.getDeleteErrorMessage(error);
          this._notification.error('Не удалось удалить задачу', this.modalErrorMessage);
        }
      });
  }

  formatHours(hours: number): string {
    return `${this.hoursFormatter.format(hours)} ч`;
  }

  formatTimeSlot(hour: number): string {
    return `${String(hour).padStart(2, '0')}:00`;
  }

  trackByDay(_index: number, day: PlannerDay): string {
    return day.iso;
  }

  trackByMiniCalendarDay(_index: number, day: MiniCalendarDay): string {
    return day.iso;
  }

  trackByTask(_index: number, task: ScheduleTask): string {
    return task.id;
  }

  trackByEvent(_index: number, plannerEvent: PlannerEvent): string {
    return plannerEvent.task.id;
  }

  trackByActualEvent(_index: number, event: ActualPlannerEvent): string {
    return event.id;
  }

  getDayTitle(day: PlannerDay): string {
    const titleParts = [this.capitalize(format(day.date, 'EEEE, d MMMM yyyy', { locale: ru }))];

    if (!day.tasks.length && !day.actualEvents.length) {
      titleParts.push('Свободно');
      titleParts.push('Двойной клик добавляет новую задачу');
      return titleParts.join(' • ');
    }

    if (day.tasks.length) {
      titleParts.push(`${day.tasks.length} задач`);
      titleParts.push(`План: ${this.formatHours(day.totalPlannedHours)}`);
    }

    if (day.totalActualHours > 0) {
      titleParts.push(`Факт: ${this.formatHours(day.totalActualHours)}`);
    }

    const taskTitles = day.tasks.slice(0, 3).map((task) => {
      const taskLabel = this.getTaskTitle(task);
      return `${task.startTime} • ${taskLabel}`;
    });
    titleParts.push(...taskTitles);

    const actualTitles = day.actualEvents
      .slice(0, 2)
      .map((event) => `${event.issueTitle} • ${event.hoursLabel}`);
    titleParts.push(...actualTitles);

    return titleParts.join(' • ');
  }

  getTaskTitle(task: ScheduleTask): string {
    return task.comment ?? 'Без названия';
  }

  toggleColorDropdown(): void {
    this.showColorDropdown = !this.showColorDropdown;
  }

  selectTaskColor(color: string): void {
    this.editorForm.get('color')?.setValue(color);
    this.showColorDropdown = false;
  }

  private openEditorForTask(iso: string, task: ScheduleTask | null, startMinutes: number): void {
    this.selectedDate = iso;
    this.selectedTask = task ? { ...task } : null;
    this.showColorDropdown = false;
    this.modalErrorMessage = '';
    this.loadWorklogIssueOptions();
    this.editorForm.reset({
      startTime: task?.startTime ?? this.formatMinutesValue(startMinutes),
      plannedHours: task?.plannedHours ?? 0,
      actualIssueId: task?.actualIssueId ?? null,
      actualHours: task?.actualHours ?? 0,
      color: task?.color ?? this.defaultTaskColor,
      comment: task?.comment ?? ''
    });
    this.showEditor = true;
  }

  private resetEditorForm(startMinutes: number): void {
    this.editorForm.reset({
      startTime: this.formatMinutesValue(startMinutes),
      plannedHours: 0,
      actualIssueId: null,
      actualHours: 0,
      color: this.defaultTaskColor,
      comment: ''
    });
  }

  private loadCurrentPeriod(): void {
    if (!this.userId) {
      return;
    }

    const period = this.getVisiblePeriod();
    this.isLoading = true;
    this.errorMessage = '';
    this.visiblePeriodLabel = this.formatPeriodLabel(period.start, period.end);
    this.weekLabel = this.formatWeekLabel(period.start, period.end);
    this.loadWorklogIssueOptions();

    forkJoin({
      schedules: this._scheduleService.listUserSchedules(this.userId, period.from, period.to),
      worklogs: this._scheduleService.listUserWorklogs(this.userId, period.from, period.to)
    })
      .pipe(
        finalize(() => {
          this.isLoading = false;
        })
      )
      .subscribe({
        next: ({ schedules, worklogs }) => {
          this.applySchedules(schedules, worklogs);
        },
        error: (error) => {
          this.serverRecordsByDate = new Map();
          this.serverWorklogsByDate = new Map();
          this.totalActualHours = 0;
          this.totalPlannedHours = 0;
          this.totalSchedules = 0;
          this.rebuildView();
          this.errorMessage = this.getLoadErrorMessage(error);
          this._notification.error('Не удалось загрузить график', this.errorMessage);
        }
      });
  }

  private applySchedules(schedules: JSchedule[], worklogs: JWorklog[]): void {
    this.serverRecordsByDate = new Map(schedules.map((schedule) => [schedule.date, schedule]));
    this.serverWorklogsByDate = this.mergeWorklogsByDate(worklogs);
    worklogs.forEach((worklog) => {
      this.ensureIssueOptionForId(worklog.issueId);
    });
    this.rebuildView();
  }

  private rebuildView(): void {
    const period = this.getVisiblePeriod();

    this.sidebarMonth = startOfMonth(this.focusedDate);
    this.visiblePeriodLabel = this.formatPeriodLabel(period.start, period.end);
    this.weekLabel = this.formatWeekLabel(period.start, period.end);
    this.plannerDays = eachDayOfInterval({ start: period.start, end: period.end }).map((date) =>
      this.buildPlannerDay(date)
    );
    this.totalSchedules = this.plannerDays.reduce((count, day) => count + day.tasks.length, 0);
    this.totalActualHours = this.plannerDays.reduce((hours, day) => hours + day.totalActualHours, 0);
    this.totalPlannedHours = this.plannerDays.reduce(
      (hours, day) => hours + day.totalPlannedHours,
      0
    );
    this.miniCalendarDays = this.buildMiniCalendarDays();
    this.updateCurrentTimeIndicator();
  }

  private buildPlannerDay(date: Date): PlannerDay {
    const iso = format(date, 'yyyy-MM-dd');
    const tasks = this.getTasksForDate(iso);
    const plannedEvents = tasks.map((task) => this.buildPlannerEvent(task));
    const actualEvents = this.toActualPlannerEvents(iso, tasks);
    const dayIndex = (date.getDay() + 6) % 7;
    const totalPlannedHours = tasks.reduce((hours, task) => hours + task.plannedHours, 0);
    const totalActualHours = actualEvents.reduce((hours, event) => hours + event.hours, 0);

    return {
      date,
      iso,
      dayNumber: date.getDate(),
      weekdayLabel: this.weekDayLabels[dayIndex],
      fullLabel: this.capitalize(format(date, 'EEEE', { locale: ru })),
      isToday: isToday(date),
      isWeekend: date.getDay() === 0 || date.getDay() === 6,
      isFocused: format(this.focusedDate, 'yyyy-MM-dd') === iso,
      tasks,
      plannedEvents,
      actualEvents,
      hasSchedules: tasks.length > 0 || actualEvents.length > 0,
      totalPlannedHours,
      totalActualHours,
      summaryLabel: this.buildDaySummaryLabel(tasks.length, totalPlannedHours, totalActualHours)
    };
  }

  private buildPlannerEvent(task: ScheduleTask): PlannerEvent {
    const startMinutes = this.parseTimeInput(task.startTime) ?? this.getDefaultStartMinutes();

    return {
      task,
      title: this.getTaskTitle(task),
      timeLabel: this.buildEventTimeLabel(startMinutes, task.plannedHours),
      style: this.buildEventStyle(task, startMinutes)
    };
  }

  private toActualPlannerEvents(iso: string, tasks: ScheduleTask[]): ActualPlannerEvent[] {
    const taskEvents = tasks
      .map((task, index) => this.toActualEventFromTask(task, index))
      .filter((event): event is ActualPlannerEvent => !!event);
    const linkedWorklogIds = new Set(
      tasks.map((task) => task.actualWorklogId).filter((value): value is string => !!value)
    );
    const unlinkedWorklogs = (this.serverWorklogsByDate.get(iso) ?? []).filter(
      (worklog) => !linkedWorklogIds.has(worklog.id)
    );
    const worklogEvents = unlinkedWorklogs.map((worklog, index) =>
      this.toActualEventFromWorklog(iso, worklog, taskEvents.length + index)
    );
    return [...taskEvents, ...worklogEvents];
  }

  private toActualEventFromTask(task: ScheduleTask, index: number): ActualPlannerEvent | null {
    if (!task.actualIssueId || !task.actualHours || task.actualHours <= 0) {
      return null;
    }

    const startMinutes = this.parseTimeInput(task.startTime) ?? this.getDefaultStartMinutes();
    const issueTitle = this.getIssueTitle(task.actualIssueId);
    const issueLabel = this.getIssueLabel(task.actualIssueId);
    return {
      id: `task-actual:${task.id}`,
      issueId: task.actualIssueId,
      issueTitle: issueLabel,
      title: issueTitle,
      timeLabel: this.buildEventTimeLabel(startMinutes, task.actualHours),
      hoursLabel: this.formatHours(task.actualHours),
      hours: task.actualHours,
      style: this.buildActualEventStyle(startMinutes, task.actualHours, index)
    };
  }

  private toActualEventFromWorklog(
    iso: string,
    worklog: JWorklog,
    index: number
  ): ActualPlannerEvent {
    const issueTitle = this.getIssueTitle(worklog.issueId);
    const issueLabel = this.getIssueLabel(worklog.issueId);
    const startMinutes = this.normalizeStartMinutes(
      this.getDerivedStartMinutes(iso) + index * this.plannerMinuteStep
    );
    const hours = this.normalizeHours(worklog.hours);
    return {
      id: `worklog:${worklog.id}`,
      issueId: worklog.issueId,
      issueTitle: issueLabel,
      title: issueTitle,
      timeLabel: this.buildEventTimeLabel(startMinutes, hours),
      hoursLabel: this.formatHours(hours),
      hours,
      style: this.buildActualEventStyle(startMinutes, hours, index)
    };
  }

  private buildMiniCalendarDays(): MiniCalendarDay[] {
    const monthStart = startOfMonth(this.sidebarMonth);
    const monthEnd = endOfMonth(this.sidebarMonth);
    const start = startOfWeek(monthStart, { weekStartsOn: 1 });
    const end = endOfWeek(monthEnd, { weekStartsOn: 1 });

    return eachDayOfInterval({ start, end }).map((date) => {
      const iso = format(date, 'yyyy-MM-dd');

      return {
        date,
        iso,
        dayNumber: date.getDate(),
        isCurrentMonth: isSameMonth(date, this.sidebarMonth),
        isToday: isToday(date),
        isFocused: format(this.focusedDate, 'yyyy-MM-dd') === iso,
        isInFocusedWeek: isSameWeek(date, this.focusedDate, { weekStartsOn: 1 }),
        hasSchedule: this.getTasksForDate(iso).length > 0 || (this.serverWorklogsByDate.get(iso) ?? []).length > 0
      };
    });
  }

  private buildEventStyle(task: ScheduleTask, startMinutes: number): Record<string, string> {
    const plannerStartMinutes = this.plannerStartHour * 60;
    const plannerDurationMinutes = this.timeSlots.length * 60;
    const availableMinutes = this.plannerEndHour * 60 - startMinutes;
    const clampedMinutes = Math.min(Math.max(task.plannedHours * 60, 0), availableMinutes);
    const visibleMinutes = clampedMinutes > 0 ? clampedMinutes : this.plannerMinuteStep;
    const top = ((startMinutes - plannerStartMinutes) / 60) * this.plannerRowHeight;
    const maxHeight = plannerDurationMinutes
      ? (plannerDurationMinutes / 60) * this.plannerRowHeight - top
      : 0;
    const baseHeight = (visibleMinutes / 60) * this.plannerRowHeight;
    const minHeight = Math.min(task.plannedHours > 0 ? 52 : 44, maxHeight);
    const height = Math.min(Math.max(baseHeight, minHeight), maxHeight);

    return {
      top: `${top}px`,
      height: `${height}px`,
      '--schedule-event-color': task.color,
      zIndex: '1'
    };
  }

  private buildActualEventStyle(
    startMinutes: number,
    hours: number,
    layerIndex: number
  ): Record<string, string> {
    const plannerStartMinutes = this.plannerStartHour * 60;
    const plannerDurationMinutes = this.timeSlots.length * 60;
    const availableMinutes = this.plannerEndHour * 60 - startMinutes;
    const clampedMinutes = Math.min(Math.max(hours * 60, 0), availableMinutes);
    const visibleMinutes = clampedMinutes > 0 ? clampedMinutes : this.plannerMinuteStep;
    const top = ((startMinutes - plannerStartMinutes) / 60) * this.plannerRowHeight;
    const maxHeight = plannerDurationMinutes
      ? (plannerDurationMinutes / 60) * this.plannerRowHeight - top
      : 0;
    const baseHeight = (visibleMinutes / 60) * this.plannerRowHeight;
    const minHeight = Math.min(hours > 0 ? 50 : 44, maxHeight);
    const height = Math.min(Math.max(baseHeight, minHeight), maxHeight);
    return {
      top: `${top}px`,
      height: `${height}px`,
      '--schedule-event-color': this.actualTaskColor,
      zIndex: String(3 + layerIndex)
    };
  }

  private buildEventTimeLabel(startMinutes: number, hours: number): string {
    if (hours <= 0) {
      return `${this.formatMinutesValue(startMinutes)} • заметка`;
    }

    const endMinutes = Math.min(
      startMinutes + Math.round(hours * 60),
      this.plannerEndHour * 60
    );

    return `${this.formatMinutesValue(startMinutes)} - ${this.formatMinutesValue(endMinutes)}`;
  }

  private buildDaySummaryLabel(
    taskCount: number,
    totalPlannedHours: number,
    totalActualHours: number
  ): string {
    if (!taskCount && totalActualHours <= 0) {
      return 'Свободно';
    }

    const parts: string[] = [];
    if (taskCount === 1) {
      parts.push(this.formatHours(totalPlannedHours));
    } else if (taskCount > 1) {
      parts.push(`${this.formatHours(totalPlannedHours)} • ${taskCount} задач`);
    }
    if (totalActualHours > 0) {
      parts.push(`Факт ${this.formatHours(totalActualHours)}`);
    }
    return parts.join(' • ');
  }

  private updateCurrentTimeIndicator(): void {
    const today = this.plannerDays.find((day) => day.isToday);

    if (!today) {
      this.currentTimeIndicator = null;
      return;
    }

    const now = new Date();
    const hourValue = now.getHours() + now.getMinutes() / 60;

    if (hourValue < this.plannerStartHour || hourValue > this.plannerEndHour) {
      this.currentTimeIndicator = null;
      return;
    }

    this.currentTimeIndicator = {
      dayIso: today.iso,
      top: `${(hourValue - this.plannerStartHour) * this.plannerRowHeight}px`
    };
  }

  private buildDayMutationRequest(iso: string, tasks: ScheduleTask[]): Observable<JSchedule | void> | null {
    if (!this.userId) {
      return null;
    }

    const serverRecord = this.serverRecordsByDate.get(iso) ?? null;
    const totalHours = this.normalizeHours(tasks.reduce((hours, task) => hours + task.plannedHours, 0));
    const dayComment = this.buildDayCommentSummary(tasks);

    if (!tasks.length) {
      return serverRecord ? this._scheduleService.deleteSchedule(serverRecord.id) : null;
    }

    if (!serverRecord) {
      return this._scheduleService.createSchedule(this.userId, {
        date: iso,
        plannedHours: totalHours,
        comment: dayComment
      });
    }

    const payload: UpdateSchedulePayload = {};

    if (this.normalizeHours(serverRecord.plannedHours) !== totalHours) {
      payload.plannedHours = totalHours;
    }

    if ((serverRecord.comment ?? null) !== (dayComment ?? null)) {
      payload.comment = dayComment;
    }

    return Object.keys(payload).length
      ? this._scheduleService.updateSchedule(serverRecord.id, payload)
      : null;
  }

  private buildActualMutationRequest(
    iso: string,
    nextTask: ScheduleTask,
    previousTask: ScheduleTask | null
  ): Observable<{ actualWorklog: JWorklog | null }> | null {
    const nextIssueId = nextTask.actualIssueId;
    const nextHours = nextTask.actualHours ?? 0;
    const previousWorklogId = previousTask?.actualWorklogId ?? null;
    const previousIssueId = previousTask?.actualIssueId ?? null;
    const comment = this.normalizeComment(nextTask.comment);

    if (!nextIssueId || nextHours <= 0) {
      if (!previousWorklogId) {
        return null;
      }
      return this._scheduleService
        .deleteWorklog(previousWorklogId)
        .pipe(map(() => ({ actualWorklog: null })));
    }

    if (previousWorklogId) {
      if (previousIssueId && previousIssueId !== nextIssueId) {
        return this._scheduleService.deleteWorklog(previousWorklogId).pipe(
          switchMap(() =>
            this._scheduleService.createIssueWorklog(nextIssueId, {
              workDate: iso,
              hours: nextHours,
              comment
            })
          ),
          map((actualWorklog) => ({ actualWorklog }))
        );
      }

      return this._scheduleService
        .updateWorklog(previousWorklogId, {
          workDate: iso,
          hours: nextHours,
          comment
        })
        .pipe(map((actualWorklog) => ({ actualWorklog })));
    }

    return this._scheduleService
      .createIssueWorklog(nextIssueId, {
        workDate: iso,
        hours: nextHours,
        comment
      })
      .pipe(map((actualWorklog) => ({ actualWorklog })));
  }

  private executePersistRequests(
    scheduleRequest$: Observable<JSchedule | void> | null,
    actualRequest$: Observable<{ actualWorklog: JWorklog | null }> | null
  ): Observable<{ actualWorklog: JWorklog | null | undefined }> {
    if (!scheduleRequest$ && !actualRequest$) {
      return of({ actualWorklog: undefined });
    }

    const schedule$ = scheduleRequest$ ?? of(void 0);
    const actual$ =
      actualRequest$ ?? of({ actualWorklog: undefined as JWorklog | null | undefined });
    return forkJoin({ schedule: schedule$, actual: actual$ }).pipe(
      map(({ actual }) => ({
        actualWorklog: actual.actualWorklog
      }))
    );
  }

  private applyActualMutationResult(
    task: ScheduleTask,
    actualWorklog: JWorklog | null | undefined
  ): ScheduleTask {
    if (actualWorklog === undefined) {
      return task;
    }
    if (actualWorklog === null) {
      return {
        ...task,
        actualWorklogId: null,
        actualIssueId: null,
        actualHours: null
      };
    }
    this.ensureIssueOptionForId(actualWorklog.issueId);
    return {
      ...task,
      actualWorklogId: actualWorklog.id,
      actualIssueId: actualWorklog.issueId,
      actualHours: this.normalizeHours(actualWorklog.hours)
    };
  }

  private getVisiblePeriod(): { start: Date; end: Date; from: string; to: string } {
    const start = startOfWeek(this.focusedDate, { weekStartsOn: 1 });
    const end = endOfWeek(this.focusedDate, { weekStartsOn: 1 });

    return {
      start,
      end,
      from: format(start, 'yyyy-MM-dd'),
      to: format(end, 'yyyy-MM-dd')
    };
  }

  private getLoadErrorMessage(error: any): string {
    if (error?.status === 403) {
      return 'Нет доступа к личному графику. Проверьте активную учетную запись.';
    }

    return getApiErrorMessage(
      error,
      'Не удалось получить записи за выбранный период. Повторите попытку.'
    );
  }

  private getMutationErrorMessage(error: any): string {
    if (error?.status === 403) {
      return 'Нет доступа к редактированию этого графика.';
    }

    if (error?.status === 409) {
      return 'Запись на эту дату уже существует. Обновите календарь и повторите попытку.';
    }

    if (error?.status === 400) {
      return getApiErrorMessage(
        error,
        'Проверьте корректность часов. Задача не должна выходить за границы рабочего дня.'
      );
    }

    return getApiErrorMessage(error, 'Не удалось сохранить задачу календаря.');
  }

  private getDeleteErrorMessage(error: any): string {
    if (error?.status === 403) {
      return 'Нет доступа к удалению этой записи.';
    }

    return getApiErrorMessage(error, 'Не удалось удалить задачу календаря.');
  }

  private setFocusedDate(date: Date, reload: boolean): void {
    this.focusedDate = this.stripTime(date);
    this.sidebarMonth = startOfMonth(this.focusedDate);

    if (reload) {
      this.loadCurrentPeriod();
      return;
    }

    this.rebuildView();
  }

  private formatPeriodLabel(start: Date, end: Date): string {
    const startLabel = format(start, 'd MMMM', { locale: ru });
    const endLabel = format(end, 'd MMMM yyyy', { locale: ru });

    return `${this.capitalize(startLabel)} - ${endLabel}`;
  }

  private formatWeekLabel(start: Date, end: Date): string {
    if (isSameMonth(start, end)) {
      return `${format(start, 'd', { locale: ru })} - ${format(end, 'd MMMM yyyy', {
        locale: ru
      })}`;
    }

    return `${format(start, 'd MMM', { locale: ru })} - ${format(end, 'd MMM yyyy', {
      locale: ru
    })}`;
  }

  private formatMinutesValue(totalMinutes: number): string {
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;

    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
  }

  private parseTimeInput(value: unknown): number | null {
    const trimmedValue = String(value ?? '').trim();
    const match = /^(\d{2}):(\d{2})$/.exec(trimmedValue);

    if (!match) {
      return null;
    }

    const hours = Number(match[1]);
    const minutes = Number(match[2]);

    if (
      Number.isNaN(hours) ||
      Number.isNaN(minutes) ||
      hours < 0 ||
      hours > 23 ||
      minutes < 0 ||
      minutes > 59
    ) {
      return null;
    }

    const totalMinutes = hours * 60 + minutes;
    const minMinutes = this.plannerStartHour * 60;
    const maxMinutes = this.plannerEndHour * 60 - this.plannerMinuteStep;

    if (
      totalMinutes < minMinutes ||
      totalMinutes > maxMinutes ||
      totalMinutes % this.plannerMinuteStep !== 0
    ) {
      return null;
    }

    return totalMinutes;
  }

  private normalizeTimeInput(value: unknown): string | null {
    const parsed = this.parseTimeInput(value);
    return parsed === null ? null : this.formatMinutesValue(parsed);
  }

  private buildTimezoneLabel(): string {
    const offset = -new Date().getTimezoneOffset();
    const sign = offset >= 0 ? '+' : '-';
    const absoluteOffset = Math.abs(offset);
    const hours = String(Math.floor(absoluteOffset / 60)).padStart(2, '0');
    const minutes = String(absoluteOffset % 60).padStart(2, '0');

    return `GMT${sign}${hours}:${minutes}`;
  }

  private parseIsoDate(value: string): Date {
    const [year, month, day] = value.split('-').map((chunk) => Number(chunk));
    return new Date(year, month - 1, day);
  }

  private resolveStartMinutesFromPointer(event: MouseEvent): number {
    const currentTarget = event.currentTarget as HTMLElement | null;

    if (!currentTarget) {
      return this.getDefaultStartMinutes();
    }

    const rect = currentTarget.getBoundingClientRect();
    const offsetY = Math.max(0, Math.min(event.clientY - rect.top, rect.height));
    const totalPlannerMinutes = this.timeSlots.length * 60;
    const rawMinutes = this.plannerStartHour * 60 + (offsetY / rect.height) * totalPlannerMinutes;

    return this.normalizeStartMinutes(rawMinutes);
  }

  private normalizeStartMinutes(rawMinutes: number): number {
    const minMinutes = this.plannerStartHour * 60;
    const maxMinutes = this.plannerEndHour * 60 - this.plannerMinuteStep;
    const snappedMinutes =
      Math.round(rawMinutes / this.plannerMinuteStep) * this.plannerMinuteStep;

    return Math.min(Math.max(snappedMinutes, minMinutes), maxMinutes);
  }

  private getCurrentStartMinutes(date: Date): number {
    return this.normalizeStartMinutes(date.getHours() * 60 + date.getMinutes());
  }

  private getSuggestedStartMinutesForDay(iso: string): number {
    const tasks = this.getTasksForDate(iso);

    if (!tasks.length) {
      return this.getDerivedStartMinutes(iso);
    }

    const latestEndMinutes = tasks.reduce((latestEnd, task) => {
      const taskStartMinutes = this.parseTimeInput(task.startTime) ?? this.getDefaultStartMinutes();
      const taskEndMinutes = taskStartMinutes + Math.round(task.plannedHours * 60);
      return Math.max(latestEnd, taskEndMinutes);
    }, this.getDefaultStartMinutes());

    return this.normalizeStartMinutes(latestEndMinutes);
  }

  private getDerivedStartMinutes(iso: string): number {
    const legacyMinutes = this.readLegacyDisplayStartMinutes(iso);
    return legacyMinutes ?? this.getDefaultStartMinutes();
  }

  private getDefaultStartMinutes(): number {
    return this.defaultShiftStartHour * 60;
  }

  private buildDayCommentSummary(tasks: ScheduleTask[]): string | null {
    const titles = tasks
      .map((task) => this.normalizeComment(task.comment))
      .filter((value): value is string => !!value);

    if (!titles.length) {
      return tasks.length > 1 ? `${tasks.length} задач` : null;
    }

    const prefix = tasks.length > 1 ? `${tasks.length} задач: ` : '';
    const summary = `${prefix}${titles.slice(0, 3).join('; ')}`;

    return summary.length > 1000 ? `${summary.slice(0, 997)}...` : summary;
  }

  private mergeTaskIntoDay(iso: string, task: ScheduleTask): ScheduleTask[] {
    const currentTasks = this.getTasksForDate(iso);
    const existingTaskIndex = currentTasks.findIndex((currentTask) => currentTask.id === task.id);
    const nextTask = { ...task, source: 'local' as const };

    if (existingTaskIndex >= 0) {
      currentTasks.splice(existingTaskIndex, 1, nextTask);
    } else {
      currentTasks.push(nextTask);
    }

    return this.sortTasks(currentTasks);
  }

  private getTasksForDate(iso: string): ScheduleTask[] {
    const localTasks = this.localTasksByDate.get(iso);

    if (localTasks?.length) {
      return this.sortTasks(localTasks.map((task) => ({ ...task })));
    }

    const serverRecord = this.serverRecordsByDate.get(iso);
    if (!serverRecord) {
      return [];
    }

    return [
      {
        id: `server:${serverRecord.id}`,
        date: iso,
        startTime: this.formatMinutesValue(this.getDerivedStartMinutes(iso)),
        plannedHours: serverRecord.plannedHours,
        color: this.defaultTaskColor,
        comment: serverRecord.comment,
        actualWorklogId: null,
        actualIssueId: null,
        actualHours: null,
        source: 'derived'
      }
    ];
  }

  private sortTasks(tasks: ScheduleTask[]): ScheduleTask[] {
    return [...tasks].sort((left, right) => {
      const leftMinutes = this.parseTimeInput(left.startTime) ?? this.getDefaultStartMinutes();
      const rightMinutes = this.parseTimeInput(right.startTime) ?? this.getDefaultStartMinutes();

      if (leftMinutes !== rightMinutes) {
        return leftMinutes - rightMinutes;
      }

      return left.id.localeCompare(right.id);
    });
  }

  private applyLocalTasksForDate(iso: string, tasks: ScheduleTask[]): void {
    if (!tasks.length) {
      this.localTasksByDate.delete(iso);
      this.persistLocalTasks();
      return;
    }

    this.localTasksByDate.set(
      iso,
      this.sortTasks(tasks).map((task) => ({
        ...task,
        source: 'local'
      }))
    );
    this.persistLocalTasks();
  }

  private loadLocalTasks(): void {
    this.localTasksByDate = new Map();

    if (typeof window === 'undefined' || !window.localStorage) {
      return;
    }

    try {
      const rawValue = window.localStorage.getItem(this.getLocalTasksStorageKey());
      if (!rawValue) {
        return;
      }

      const parsedValue = JSON.parse(rawValue);
      if (!Array.isArray(parsedValue)) {
        return;
      }

      parsedValue.forEach((entry) => {
        const task = this.normalizeStoredTask(entry);
        if (!task) {
          return;
        }

        const dayTasks = this.localTasksByDate.get(task.date) ?? [];
        dayTasks.push(task);
        this.localTasksByDate.set(task.date, dayTasks);
      });

      Array.from(this.localTasksByDate.keys()).forEach((dateKey) => {
        const tasks = this.localTasksByDate.get(dateKey) ?? [];
        this.localTasksByDate.set(dateKey, this.sortTasks(tasks));
      });
    } catch (_error) {
      this.localTasksByDate = new Map();
    }
  }

  private persistLocalTasks(): void {
    if (typeof window === 'undefined' || !window.localStorage) {
      return;
    }

    const flattenedTasks = Array.from(this.localTasksByDate.values())
      .reduce((acc, dayTasks) => acc.concat(dayTasks), [] as ScheduleTask[])
      .map((task) => ({
        id: task.id,
        date: task.date,
        startTime: task.startTime,
        plannedHours: task.plannedHours,
        actualWorklogId: task.actualWorklogId,
        actualIssueId: task.actualIssueId,
        actualHours: task.actualHours,
        color: task.color,
        comment: task.comment
      }));

    if (!flattenedTasks.length) {
      window.localStorage.removeItem(this.getLocalTasksStorageKey());
      return;
    }

    window.localStorage.setItem(this.getLocalTasksStorageKey(), JSON.stringify(flattenedTasks));
  }

  private getLocalTasksStorageKey(): string {
    return `schedule-day-tasks:${this.userId ?? 'anonymous'}`;
  }

  private normalizeStoredTask(value: any): ScheduleTask | null {
    if (!value || typeof value !== 'object') {
      return null;
    }

    const date = String(value.date ?? '').trim();
    const id = String(value.id ?? '').trim();
    const startTime = this.normalizeTimeInput(value.startTime);
    const plannedHours = Number(value.plannedHours ?? 0);
    const actualWorklogId = this.normalizeIssueId(value.actualWorklogId);
    const actualIssueId = this.normalizeIssueId(value.actualIssueId);
    const rawActualHours = Number(value.actualHours ?? 0);
    const actualHours =
      Number.isFinite(rawActualHours) && rawActualHours > 0 ? this.normalizeHours(rawActualHours) : null;
    const color = this.normalizeColor(value.color);
    const comment = this.normalizeComment(value.comment);

    if (!date || !id || !startTime || !color || Number.isNaN(plannedHours) || plannedHours < 0) {
      return null;
    }

    if (actualHours !== null && !actualIssueId) {
      return null;
    }

    return {
      id,
      date,
      startTime,
      plannedHours: this.normalizeHours(plannedHours),
      actualWorklogId: actualWorklogId ?? null,
      actualIssueId: actualIssueId ?? null,
      actualHours,
      color,
      comment,
      source: 'local'
    };
  }

  private loadWorklogIssueOptions(): void {
    if (this.isLoadingIssueOptions || this.worklogIssueOptions.length > 0) {
      return;
    }

    this.isLoadingIssueOptions = true;
    this._scheduleService
      .listWorklogIssueOptions()
      .pipe(
        finalize(() => {
          this.isLoadingIssueOptions = false;
        })
      )
      .subscribe({
        next: (issues) => {
          this.worklogIssueOptions = issues;
          this.worklogIssueOptionsById = new Map(issues.map((issue) => [issue.id, issue]));
          this.rebuildView();
        },
        error: () => {
          this.worklogIssueOptions = [];
          this.worklogIssueOptionsById = new Map();
        }
      });
  }

  private mergeWorklogsByDate(worklogs: JWorklog[]): Map<string, JWorklog[]> {
    const grouped = new Map<string, JWorklog[]>();
    worklogs.forEach((worklog) => {
      const dayWorklogs = grouped.get(worklog.workDate) ?? [];
      dayWorklogs.push(worklog);
      grouped.set(worklog.workDate, dayWorklogs);
    });
    return grouped;
  }

  private normalizeIssueId(value: unknown): string | null {
    const normalizedValue = String(value ?? '').trim();
    return normalizedValue ? normalizedValue : null;
  }

  private ensureIssueOptionForId(issueId: string): void {
    if (!issueId || this.worklogIssueOptionsById.has(issueId)) {
      return;
    }

    const fallbackOption: WorklogIssueOption = {
      id: issueId,
      key: '',
      title: 'Задача',
      label: 'Задача'
    };
    this.worklogIssueOptionsById.set(issueId, fallbackOption);
    this.worklogIssueOptions = [...this.worklogIssueOptions, fallbackOption].sort((left, right) =>
      left.label.localeCompare(right.label, 'ru')
    );
  }

  private getIssueLabel(issueId: string): string {
    return this.worklogIssueOptionsById.get(issueId)?.label ?? 'Задача';
  }

  private getIssueTitle(issueId: string): string {
    return this.worklogIssueOptionsById.get(issueId)?.title ?? 'Задача';
  }

  private readLegacyDisplayStartMinutes(iso: string): number | null {
    if (typeof window === 'undefined' || !window.localStorage) {
      return null;
    }

    const rawValue = window.localStorage.getItem(this.getLegacyDisplayStartStorageKey(iso));
    const parsedValue = Number(rawValue);

    return Number.isFinite(parsedValue) ? this.parseTimeInput(this.formatMinutesValue(parsedValue)) : null;
  }

  private getLegacyDisplayStartStorageKey(iso: string): string {
    return `schedule-display-start:${this.userId ?? 'anonymous'}:${iso}`;
  }

  private generateTaskId(iso: string): string {
    return `task:${iso}:${Date.now()}:${Math.random().toString(36).slice(2, 9)}`;
  }

  private getMaxPlannedHoursForStartMinutes(startMinutes: number): number {
    return this.normalizeHours((this.plannerEndHour * 60 - startMinutes) / 60);
  }

  private normalizeHours(value: number): number {
    return Math.round(value * 10) / 10;
  }

  private validateStartTime(control: AbstractControl): ValidationErrors | null {
    if (control.value === null || control.value === undefined || control.value === '') {
      return null;
    }

    return this.parseTimeInput(control.value) === null ? { invalidTime: true } : null;
  }

  private validatePlannedHours(control: AbstractControl): ValidationErrors | null {
    if (control.value === null || control.value === undefined || control.value === '') {
      return null;
    }

    const plannedHours = Number(control.value);
    if (Number.isNaN(plannedHours)) {
      return { invalidHours: true };
    }

    const startMinutes = this.parseTimeInput(this.editorForm?.get('startTime')?.value);
    if (startMinutes === null) {
      return null;
    }

    return plannedHours > this.getMaxPlannedHoursForStartMinutes(startMinutes)
      ? { exceedsWorkday: true }
      : null;
  }

  private stripTime(date: Date): Date {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate());
  }

  private normalizeComment(comment: unknown): string | null {
    const trimmedComment = String(comment ?? '').trim();
    return trimmedComment ? trimmedComment : null;
  }

  private normalizeColor(color: unknown): string | null {
    const normalizedColor = String(color ?? '').trim().toLowerCase();
    return /^#[0-9a-f]{6}$/.test(normalizedColor) ? normalizedColor : null;
  }

  private capitalize(value: string): string {
    return value ? value.charAt(0).toUpperCase() + value.slice(1) : value;
  }
}
