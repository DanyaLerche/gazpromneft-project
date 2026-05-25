import { Component, ElementRef, forwardRef, HostListener, Input, OnChanges, SimpleChanges } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';
import { DateUtil } from '@trungk18/project/utils/date';

type CalendarDay = {
  iso: string;
  label: number;
  isCurrentMonth: boolean;
  isToday: boolean;
  isSelected: boolean;
  isDisabled: boolean;
};

@Component({
  selector: 'project-date-input',
  templateUrl: './project-date-input.component.html',
  styleUrls: ['./project-date-input.component.scss'],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => ProjectDateInputComponent),
      multi: true
    }
  ]
})
export class ProjectDateInputComponent implements ControlValueAccessor, OnChanges {
  @Input() min: string | null = null;
  @Input() max: string | null = null;
  @Input() placeholder = 'дд.мм.гггг';
  @Input() label = 'Выберите дату';
  @Input() size: 'default' | 'large' = 'default';
  @Input() disabled = false;

  readonly weekDayLabels = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

  calendarDays: CalendarDay[] = [];
  displayValue = '';
  isOpen = false;
  viewMonth = ProjectDateInputComponent.getMonthStart(new Date());

  private value: string | null = null;
  private onChange: (value: string | null) => void = () => undefined;
  private onTouched: () => void = () => undefined;

  constructor(private readonly elementRef: ElementRef<HTMLElement>) {
    this.rebuildCalendar();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['disabled']?.currentValue) {
      this.isOpen = false;
    }

    if (changes['min'] || changes['max']) {
      this.rebuildCalendar();
    }
  }

  writeValue(value: string | null): void {
    this.value = DateUtil.formatDateOnly(value);
    this.displayValue = this.formatDisplayValue(this.value);
    this.syncViewMonth();
    this.rebuildCalendar();
  }

  registerOnChange(fn: (value: string | null) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    this.disabled = isDisabled;
    if (isDisabled) {
      this.isOpen = false;
    }
  }

  get monthLabel(): string {
    const formattedMonth = new Intl.DateTimeFormat('ru-RU', {
      month: 'long',
      year: 'numeric'
    }).format(this.viewMonth);

    return formattedMonth.charAt(0).toUpperCase() + formattedMonth.slice(1);
  }

  togglePanel(event?: MouseEvent): void {
    event?.stopPropagation();
    event?.preventDefault();

    if (this.disabled) {
      return;
    }

    this.isOpen = !this.isOpen;
    if (this.isOpen) {
      this.syncViewMonth();
      this.rebuildCalendar();
    }
  }

  openPanel(): void {
    if (this.disabled || this.isOpen) {
      return;
    }

    this.isOpen = true;
    this.syncViewMonth();
    this.rebuildCalendar();
  }

  closePanel(): void {
    this.isOpen = false;
  }

  previousMonth(): void {
    this.viewMonth = new Date(this.viewMonth.getFullYear(), this.viewMonth.getMonth() - 1, 1);
    this.rebuildCalendar();
  }

  nextMonth(): void {
    this.viewMonth = new Date(this.viewMonth.getFullYear(), this.viewMonth.getMonth() + 1, 1);
    this.rebuildCalendar();
  }

  onManualInput(event: Event): void {
    const nextDisplayValue = (event.target as HTMLInputElement).value;
    this.displayValue = nextDisplayValue;

    if (!nextDisplayValue.trim()) {
      this.commitValue(null, false);
      return;
    }

    const parsedDate = this.parseDisplayValue(nextDisplayValue);
    if (!parsedDate) {
      return;
    }

    const nextValue = this.toIso(parsedDate);
    if (this.isDisabledDate(nextValue)) {
      return;
    }

    this.commitValue(nextValue, false);
    this.viewMonth = ProjectDateInputComponent.getMonthStart(parsedDate);
    this.rebuildCalendar();
  }

  onEnter(event: KeyboardEvent): void {
    event.preventDefault();

    if (!this.displayValue.trim()) {
      this.commitValue(null, true);
      return;
    }

    const parsedDate = this.parseDisplayValue(this.displayValue);
    if (!parsedDate) {
      this.displayValue = this.formatDisplayValue(this.value);
      this.closePanel();
      return;
    }

    const nextValue = this.toIso(parsedDate);
    if (this.isDisabledDate(nextValue)) {
      this.displayValue = this.formatDisplayValue(this.value);
      this.closePanel();
      return;
    }

    this.commitValue(nextValue, true);
  }

  onEscape(): void {
    this.displayValue = this.formatDisplayValue(this.value);
    this.closePanel();
  }

  onBlur(): void {
    this.onTouched();

    window.setTimeout(() => {
      if (!this.isOpen) {
        this.displayValue = this.formatDisplayValue(this.value);
      }
    }, 0);
  }

  clear(event: MouseEvent): void {
    event.preventDefault();
    event.stopPropagation();

    this.commitValue(null, false);
    this.displayValue = '';
    this.openPanel();
  }

  selectDate(day: CalendarDay): void {
    if (day.isDisabled) {
      return;
    }

    this.commitValue(day.iso, true);
  }

  @HostListener('document:mousedown', ['$event'])
  handleDocumentMousedown(event: MouseEvent): void {
    if (!this.elementRef.nativeElement.contains(event.target as Node)) {
      this.displayValue = this.formatDisplayValue(this.value);
      this.closePanel();
      this.onTouched();
    }
  }

  private commitValue(value: string | null, closePanel: boolean): void {
    this.value = value;
    this.displayValue = this.formatDisplayValue(value);
    this.onChange(value);
    this.rebuildCalendar();

    if (closePanel) {
      this.closePanel();
      this.onTouched();
    }
  }

  private rebuildCalendar(): void {
    const monthStart = ProjectDateInputComponent.getMonthStart(this.viewMonth);
    const monthStartDay = (monthStart.getDay() + 6) % 7;
    const calendarStart = new Date(monthStart.getFullYear(), monthStart.getMonth(), 1 - monthStartDay);
    const today = this.toIso(new Date());

    this.calendarDays = Array.from({ length: 42 }, (_, index) => {
      const currentDate = new Date(calendarStart.getFullYear(), calendarStart.getMonth(), calendarStart.getDate() + index);
      const currentIso = this.toIso(currentDate);

      return {
        iso: currentIso,
        label: currentDate.getDate(),
        isCurrentMonth: currentDate.getMonth() === monthStart.getMonth(),
        isToday: currentIso === today,
        isSelected: currentIso === this.value,
        isDisabled: this.isDisabledDate(currentIso)
      };
    });
  }

  private syncViewMonth(): void {
    const baseDate = this.value ? this.parseIsoValue(this.value) : new Date();
    this.viewMonth = ProjectDateInputComponent.getMonthStart(baseDate ?? new Date());
  }

  private formatDisplayValue(value: string | null): string {
    if (!value) {
      return '';
    }

    const [year, month, day] = value.split('-');
    return `${day}.${month}.${year}`;
  }

  private parseDisplayValue(value: string): Date | null {
    const trimmedValue = value.trim();

    if (/^\d{4}-\d{2}-\d{2}$/.test(trimmedValue)) {
      return this.parseIsoValue(trimmedValue);
    }

    const match = trimmedValue.match(/^(\d{2})\.(\d{2})\.(\d{4})$/);
    if (!match) {
      return null;
    }

    const [, day, month, year] = match;
    return ProjectDateInputComponent.createDate(Number(year), Number(month), Number(day));
  }

  private parseIsoValue(value: string): Date | null {
    const [year, month, day] = value.split('-').map((chunk) => Number(chunk));
    return ProjectDateInputComponent.createDate(year, month, day);
  }

  private isDisabledDate(value: string): boolean {
    return !!this.min && value < this.min || !!this.max && value > this.max;
  }

  private toIso(date: Date): string {
    const year = date.getFullYear();
    const month = `${date.getMonth() + 1}`.padStart(2, '0');
    const day = `${date.getDate()}`.padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  private static getMonthStart(date: Date): Date {
    return new Date(date.getFullYear(), date.getMonth(), 1);
  }

  private static createDate(year: number, month: number, day: number): Date | null {
    if (!year || !month || !day) {
      return null;
    }

    const candidate = new Date(year, month - 1, day);
    return candidate.getFullYear() === year
      && candidate.getMonth() === month - 1
      && candidate.getDate() === day
      ? candidate
      : null;
  }
}
