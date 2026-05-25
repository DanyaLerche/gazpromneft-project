export class DateUtil {
  static getNow(): string {
    return new Date().toISOString();
  }

  static formatDateOnly(
    value: Date | string | null | undefined | { toDate?: () => Date; format?: (pattern: string) => string; $d?: Date }
  ): string | null {
    if (!value) {
      return null;
    }

    if (typeof value === 'string') {
      const normalizedValue = value.trim();
      if (!normalizedValue) {
        return null;
      }

      const dateOnlyValue = normalizedValue.includes('T')
        ? normalizedValue.slice(0, 10)
        : normalizedValue;

      return /^\d{4}-\d{2}-\d{2}$/.test(dateOnlyValue) ? dateOnlyValue : null;
    }

    if (DateUtil.hasFormat(value)) {
      const formattedValue = value.format('YYYY-MM-DD');
      return formattedValue?.trim() ? formattedValue : null;
    }

    const nativeDate = DateUtil.toNativeDate(value);
    if (!nativeDate) {
      return null;
    }

    const year = nativeDate.getFullYear();
    const month = `${nativeDate.getMonth() + 1}`.padStart(2, '0');
    const day = `${nativeDate.getDate()}`.padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  static parseDateOnly(value: string | null | undefined): Date | null {
    if (!value) {
      return null;
    }

    const [year, month, day] = value.split('-').map((chunk) => Number(chunk));
    if (!year || !month || !day) {
      return null;
    }

    return new Date(year, month - 1, day);
  }

  static isDateRangeInvalid(startDate: string | null | undefined, dueDate: string | null | undefined): boolean {
    return !!startDate && !!dueDate && dueDate < startDate;
  }

  static isOverdue(dueDate: string | null | undefined, resolvedAt?: string | null): boolean {
    if (!dueDate || resolvedAt) {
      return false;
    }

    const today = DateUtil.formatDateOnly(new Date());
    return !!today && dueDate < today;
  }

  private static toNativeDate(
    value: Date | { toDate?: () => Date; $d?: Date }
  ): Date | null {
    if (value instanceof Date) {
      return value;
    }

    if (typeof value.toDate === 'function') {
      return value.toDate();
    }

    if (value.$d instanceof Date) {
      return value.$d;
    }

    return null;
  }

  private static hasFormat(
    value: Date | { format?: (pattern: string) => string }
  ): value is { format: (pattern: string) => string } {
    return typeof (value as { format?: (pattern: string) => string }).format === 'function';
  }
}
