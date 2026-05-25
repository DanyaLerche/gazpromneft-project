import { Component, OnInit } from '@angular/core';
import { getApiErrorMessage } from '@trungk18/core/utils/api-error';
import { JProjectDashboardReport } from '@trungk18/interface/project';
import { ProjectReportsService } from '@trungk18/project/state/project/project-reports.service';

type DashboardWidgetId =
  | 'taskSummary'
  | 'tasksByAssignee'
  | 'effort'
  | 'statusDistribution'
  | 'workload'
  | 'overdue'
  | 'recentActivity'
  | 'overdueTop';

type DashboardExportFormat = 'csv' | 'excel';

type DashboardWidgetOption = {
  id: DashboardWidgetId;
  label: string;
};

@Component({
  selector: 'app-project-reports',
  templateUrl: './reports.component.html',
  styleUrls: ['./reports.component.scss']
})
export class ReportsComponent implements OnInit {
  readonly breadcrumbs = ['Проекты', 'Отчеты и дашборды'];
  readonly widgetOptions: DashboardWidgetOption[] = [
    { id: 'taskSummary', label: 'Сводка задач' },
    { id: 'tasksByAssignee', label: 'Задачи по исполнителям' },
    { id: 'effort', label: 'Трудозатраты (план/факт)' },
    { id: 'statusDistribution', label: 'Распределение по статусам' },
    { id: 'workload', label: 'Нагрузка исполнителей' },
    { id: 'overdue', label: 'Просроченные задачи' },
    { id: 'recentActivity', label: 'Активность за N дней' },
    { id: 'overdueTop', label: 'Топ просроченных задач' }
  ];
  readonly defaultWidgetIds = this.widgetOptions.map((widget) => widget.id);

  report: JProjectDashboardReport | null = null;
  isLoading = false;
  errorMessage = '';
  exportErrorMessage = '';
  showWidgetSettings = false;
  visibleWidgetIds = new Set<DashboardWidgetId>(this.defaultWidgetIds);
  exportingFormat: DashboardExportFormat | null = null;

  private readonly widgetSettingsStorageKey = 'project-reports:visible-widgets';

  constructor(private _reportsService: ProjectReportsService) {}

  ngOnInit(): void {
    this.restoreWidgetSettings();
    this.loadReport();
  }

  reload() {
    this.loadReport();
  }

  exportDashboard(format: DashboardExportFormat) {
    this.exportErrorMessage = '';
    this.exportingFormat = format;

    this._reportsService.exportProjectDashboardReport(format).subscribe({
      next: (response) => {
        const filenameFromHeader = this.parseFilename(response.headers.get('Content-Disposition'));
        const filename = filenameFromHeader ?? this.buildDefaultFilename(format);
        if (response.body) {
          this.downloadBlob(response.body, filename);
        }
        this.exportingFormat = null;
      },
      error: (error) => {
        this.exportErrorMessage = getApiErrorMessage(error, 'Не удалось выгрузить дашборд.');
        this.exportingFormat = null;
      }
    });
  }

  isExporting(format: DashboardExportFormat): boolean {
    return this.exportingFormat === format;
  }

  formatPercent(value: number | null | undefined): string {
    if (value === null || value === undefined) {
      return '—';
    }
    return `${value.toFixed(2)}%`;
  }

  toggleWidgetSettings() {
    this.showWidgetSettings = !this.showWidgetSettings;
  }

  isWidgetVisible(widgetId: DashboardWidgetId): boolean {
    return this.visibleWidgetIds.has(widgetId);
  }

  onWidgetVisibilityChange(widgetId: DashboardWidgetId, event: Event) {
    const checked = (event.target as HTMLInputElement)?.checked;
    if (!checked && this.visibleWidgetIds.size === 1 && this.visibleWidgetIds.has(widgetId)) {
      return;
    }

    if (checked) {
      this.visibleWidgetIds.add(widgetId);
    } else {
      this.visibleWidgetIds.delete(widgetId);
    }
    this.persistWidgetSettings();
  }

  resetWidgetSettings() {
    this.visibleWidgetIds = new Set<DashboardWidgetId>(this.defaultWidgetIds);
    this.persistWidgetSettings();
  }

  private loadReport() {
    this.isLoading = true;
    this.errorMessage = '';
    this._reportsService.getProjectDashboardReport().subscribe({
      next: (report) => {
        this.report = report;
        this.isLoading = false;
      },
      error: (error) => {
        this.errorMessage = getApiErrorMessage(error, 'Не удалось загрузить отчеты проекта.');
        this.report = null;
        this.isLoading = false;
      }
    });
  }

  private buildDefaultFilename(format: DashboardExportFormat): string {
    const extension = format === 'excel' ? 'xls' : 'csv';
    const now = new Date();
    const stamp = `${now.getFullYear()}${this.pad(now.getMonth() + 1)}${this.pad(now.getDate())}-${this.pad(
      now.getHours()
    )}${this.pad(now.getMinutes())}${this.pad(now.getSeconds())}`;
    return `project-dashboard-${stamp}.${extension}`;
  }

  private parseFilename(contentDisposition: string | null): string | null {
    if (!contentDisposition) {
      return null;
    }

    const filenameMatch = contentDisposition.match(/filename\*?=(?:UTF-8''|")?([^";]+)/i);
    if (!filenameMatch?.[1]) {
      return null;
    }
    return decodeURIComponent(filenameMatch[1].replace(/"/g, ''));
  }

  private downloadBlob(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  private pad(value: number): string {
    return value < 10 ? `0${value}` : String(value);
  }

  private persistWidgetSettings() {
    try {
      localStorage.setItem(
        this.widgetSettingsStorageKey,
        JSON.stringify(Array.from(this.visibleWidgetIds))
      );
    } catch {
      // ignore localStorage errors
    }
  }

  private restoreWidgetSettings() {
    try {
      const rawValue = localStorage.getItem(this.widgetSettingsStorageKey);
      if (!rawValue) {
        return;
      }

      const parsedValue = JSON.parse(rawValue);
      if (!Array.isArray(parsedValue)) {
        return;
      }

      const allowedWidgetIds = new Set<DashboardWidgetId>(this.defaultWidgetIds);
      const restoredWidgetIds = parsedValue.filter((widgetId): widgetId is DashboardWidgetId =>
        allowedWidgetIds.has(widgetId as DashboardWidgetId)
      );
      if (!restoredWidgetIds.length) {
        return;
      }
      this.visibleWidgetIds = new Set<DashboardWidgetId>(restoredWidgetIds);
    } catch {
      this.visibleWidgetIds = new Set<DashboardWidgetId>(this.defaultWidgetIds);
    }
  }
}
