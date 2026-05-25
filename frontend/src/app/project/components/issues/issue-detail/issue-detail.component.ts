import { Component, ElementRef, EventEmitter, Input, OnChanges, Output, SimpleChanges, ViewChild } from '@angular/core';
import { UntilDestroy, untilDestroyed } from '@ngneat/until-destroy';
import { getApiErrorMessage } from '@trungk18/core/utils/api-error';
import { JIssueAttachment } from '@trungk18/interface/attachment';
import { JCriticality, getCriticalityColor } from '@trungk18/interface/criticality';
import { JIssue } from '@trungk18/interface/issue';
import { ProjectQuery } from '@trungk18/project/state/project/project.query';
import { ProjectService } from '@trungk18/project/state/project/project.service';
import { DateUtil } from '@trungk18/project/utils/date';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzNotificationService } from 'ng-zorro-antd/notification';
import { finalize } from 'rxjs/operators';
import { IssueDeleteModalComponent } from '../issue-delete-modal/issue-delete-modal.component';
import { DeleteIssueModel } from '@trungk18/interface/ui-model/delete-issue-model';

@Component({
  selector: 'issue-detail',
  templateUrl: './issue-detail.component.html',
  styleUrls: ['./issue-detail.component.scss']
})
@UntilDestroy()
export class IssueDetailComponent implements OnChanges {
  @Input() issue: JIssue;
  @Input() isShowFullScreenButton: boolean;
  @Input() isShowCloseButton: boolean;
  @Output() onClosed = new EventEmitter();
  @Output() onOpenIssue = new EventEmitter<string>();
  @Output() onDelete = new EventEmitter<DeleteIssueModel>();
  @ViewChild('attachmentInput') attachmentInput?: ElementRef<HTMLInputElement>;
  selectedCriticalityId: string | null = null;
  startDateValue: string | null = null;
  dueDateValue: string | null = null;
  attachments: JIssueAttachment[] = [];
  isLoadingAttachments = false;
  isUploadingAttachments = false;
  deletingAttachmentIds = new Set<string>();
  downloadingAttachmentIds = new Set<string>();
  private readonly hoursFormatter = new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 1
  });
  private currentIssueId: string | null = null;
  private pendingUploadCount = 0;

  constructor(
    public projectQuery: ProjectQuery,
    private _modalService: NzModalService,
    private _projectService: ProjectService,
    private _notification: NzNotificationService
  ) {}

  ngOnChanges(changes: SimpleChanges): void {
    this.selectedCriticalityId = this.issue?.criticalityId ?? null;
    this.startDateValue = this.issue?.startDate ?? null;
    this.dueDateValue = this.issue?.dueDate ?? null;

    const nextIssueId = this.issue?.id ?? null;
    if (!nextIssueId) {
      this.currentIssueId = null;
      this.attachments = [];
      this.isLoadingAttachments = false;
      this.isUploadingAttachments = false;
      this.pendingUploadCount = 0;
      this.deletingAttachmentIds.clear();
      this.downloadingAttachmentIds.clear();
      return;
    }

    const issueChanged = changes.issue?.currentValue !== changes.issue?.previousValue;
    if (issueChanged && this.currentIssueId !== nextIssueId) {
      this.currentIssueId = nextIssueId;
      this.attachments = [];
      this.pendingUploadCount = 0;
      this.isUploadingAttachments = false;
      this.deletingAttachmentIds.clear();
      this.downloadingAttachmentIds.clear();
      this.loadAttachments(nextIssueId);
    }
  }

  openDeleteIssueModal() {
    this._modalService.create({
      nzContent: IssueDeleteModalComponent,
      nzClosable: false,
      nzFooter: null,
      nzStyle: {
        top: '140px'
      },
      nzComponentParams: {
        issueId: this.issue.id,
        onDelete: this.onDelete
      }
    });
  }

  closeModal() {
    this.onClosed.emit();
  }

  openIssuePage() {
    this.onOpenIssue.emit(this.issue.id);
  }

  get criticalityColor(): string {
    return getCriticalityColor(this.issue?.criticalityLevel ? { level: this.issue.criticalityLevel } : null);
  }

  get isOverdue(): boolean {
    return DateUtil.isOverdue(this.issue?.dueDate, this.issue?.resolvedAt);
  }

  get canDeleteIssue(): boolean {
    return this.projectQuery.isCurrentUserProjectAdmin;
  }

  formatHours(value: number | null | undefined, fallback = 'Не указано'): string {
    return value === null || value === undefined
      ? fallback
      : `${this.hoursFormatter.format(value)} ч`;
  }

  updateCriticality(criticalityId: string | null) {
    this.selectedCriticalityId = criticalityId ?? null;
    this._projectService.updateIssue({
      id: this.issue.id,
      criticalityId: criticalityId ?? null
    });
  }

  updateStartDate(value: string | null) {
    const nextStartDate = DateUtil.formatDateOnly(value);
    const currentDueDate = DateUtil.formatDateOnly(this.dueDateValue);

    if (DateUtil.isDateRangeInvalid(nextStartDate, currentDueDate)) {
      this.startDateValue = this.issue?.startDate ?? null;
      return;
    }

    this.startDateValue = nextStartDate;
    this._projectService.updateIssue({
      id: this.issue.id,
      startDate: nextStartDate
    });
  }

  updateDueDate(value: string | null) {
    const currentStartDate = DateUtil.formatDateOnly(this.startDateValue);
    const nextDueDate = DateUtil.formatDateOnly(value);

    if (DateUtil.isDateRangeInvalid(currentStartDate, nextDueDate)) {
      this.dueDateValue = this.issue?.dueDate ?? null;
      return;
    }

    this.dueDateValue = nextDueDate;
    this._projectService.updateIssue({
      id: this.issue.id,
      dueDate: nextDueDate
    });
  }

  trackCriticality(_index: number, criticality: JCriticality): string {
    return criticality.id;
  }

  triggerAttachmentPicker() {
    this.attachmentInput?.nativeElement.click();
  }

  onAttachmentSelected(event: Event) {
    const fileList = (event.target as HTMLInputElement).files;
    if (!this.issue?.id || !fileList?.length) {
      return;
    }

    const files = Array.from(fileList).filter((file) => file.size > 0);
    if (!files.length) {
      return;
    }

    this.pendingUploadCount += files.length;
    this.isUploadingAttachments = true;
    const issueId = this.issue.id;
    files.forEach((file) => this.uploadAttachment(issueId, file));
    (event.target as HTMLInputElement).value = '';
  }

  downloadAttachment(attachment: JIssueAttachment) {
    if (this.downloadingAttachmentIds.has(attachment.id)) {
      return;
    }

    this.downloadingAttachmentIds.add(attachment.id);
    this._projectService
      .getIssueAttachmentDownloadUrl(attachment.id)
      .pipe(
        untilDestroyed(this),
        finalize(() => {
          this.downloadingAttachmentIds.delete(attachment.id);
        })
      )
      .subscribe({
        next: (downloadUrl) => {
          window.open(downloadUrl, '_blank', 'noopener');
        },
        error: (error) => {
          this._notification.error(
            'Не удалось скачать вложение',
            getApiErrorMessage(error, 'Повторите попытку позже.')
          );
        }
      });
  }

  deleteAttachment(attachment: JIssueAttachment) {
    if (this.deletingAttachmentIds.has(attachment.id)) {
      return;
    }

    this.deletingAttachmentIds.add(attachment.id);
    this._projectService
      .deleteIssueAttachment(attachment.id)
      .pipe(
        untilDestroyed(this),
        finalize(() => {
          this.deletingAttachmentIds.delete(attachment.id);
        })
      )
      .subscribe({
        next: () => {
          this.attachments = this.attachments.filter((item) => item.id !== attachment.id);
        },
        error: (error) => {
          this._notification.error(
            'Не удалось удалить вложение',
            getApiErrorMessage(error, 'Повторите попытку позже.')
          );
        }
      });
  }

  formatAttachmentSize(sizeBytes: number): string {
    if (!sizeBytes || sizeBytes < 1024) {
      return `${sizeBytes || 0} B`;
    }
    if (sizeBytes < 1024 * 1024) {
      return `${Math.round((sizeBytes / 1024) * 10) / 10} KB`;
    }

    return `${Math.round((sizeBytes / (1024 * 1024)) * 10) / 10} MB`;
  }

  trackAttachment(_index: number, attachment: JIssueAttachment): string {
    return attachment.id;
  }

  private loadAttachments(issueId: string) {
    this.isLoadingAttachments = true;
    this._projectService
      .listIssueAttachments(issueId)
      .pipe(
        untilDestroyed(this),
        finalize(() => {
          this.isLoadingAttachments = false;
        })
      )
      .subscribe({
        next: (attachments) => {
          if (this.currentIssueId !== issueId) {
            return;
          }
          this.attachments = attachments;
        },
        error: (error) => {
          if (this.currentIssueId !== issueId) {
            return;
          }
          this.attachments = [];
          this._notification.error(
            'Не удалось загрузить вложения',
            getApiErrorMessage(error, 'Повторите попытку позже.')
          );
        }
      });
  }

  private uploadAttachment(issueId: string, file: File) {
    this._projectService
      .uploadIssueAttachment(issueId, file)
      .pipe(
        untilDestroyed(this),
        finalize(() => {
          this.pendingUploadCount = Math.max(0, this.pendingUploadCount - 1);
          this.isUploadingAttachments = this.pendingUploadCount > 0;
        })
      )
      .subscribe({
        next: (attachment) => {
          if (this.currentIssueId !== issueId) {
            return;
          }
          this.attachments = [attachment, ...this.attachments.filter((item) => item.id !== attachment.id)];
        },
        error: (error) => {
          this._notification.error(
            'Не удалось загрузить вложение',
            getApiErrorMessage(error, `Файл "${file.name}" не был загружен.`)
          );
        }
      });
  }
}
