import { Component, Input, OnChanges, OnInit, SimpleChanges } from '@angular/core';
import { UntilDestroy, untilDestroyed } from '@ngneat/until-destroy';
import { JIssue } from '@trungk18/interface/issue';
import { JUser } from '@trungk18/interface/user';
import { DateUtil } from '@trungk18/project/utils/date';
import { ProjectQuery } from '@trungk18/project/state/project/project.query';
import { ProjectService } from '@trungk18/project/state/project/project.service';
import { IssueUtil } from '@trungk18/project/utils/issue';
import { NzModalService } from 'ng-zorro-antd/modal';
import { IssueModalComponent } from '../issue-modal/issue-modal.component';
import { NzNotificationService } from 'ng-zorro-antd/notification';
import { getApiErrorMessage } from '@trungk18/core/utils/api-error';

@Component({
  selector: 'task-card',
  templateUrl: './issue-card.component.html',
  styleUrls: ['./issue-card.component.scss']
})
@UntilDestroy()
export class IssueCardComponent implements OnChanges, OnInit {
  @Input() issue: JIssue;
  @Input() statusName: string;
  assignees: JUser[];
  issueTypeIcon: string;
  isOverdue = false;

  constructor(
    private _projectQuery: ProjectQuery,
    private _modalService: NzModalService,
    private _projectService: ProjectService,
    private _notification: NzNotificationService
  ) {}

  ngOnInit(): void {
    this._projectQuery.users$.pipe(untilDestroyed(this)).subscribe((users) => {
      this.assignees = this.issue.userIds
        .map((userId) => users.find((x) => x.id === userId))
        .filter((user): user is JUser => !!user);
    });
  }

  ngOnChanges(changes: SimpleChanges): void {
    const issueChange = changes.issue;
    if (issueChange?.currentValue !== issueChange.previousValue) {
      this.issueTypeIcon = IssueUtil.getIssueTypeIcon(this.issue.type);
      this.isOverdue = DateUtil.isOverdue(this.issue?.dueDate, this.issue?.resolvedAt);
    }
  }

  get hasPlannedEffort(): boolean {
    return this.issue?.estimate !== null && this.issue?.estimate !== undefined;
  }

  get commentsCount(): number {
    return this.issue?.comments?.length ?? 0;
  }

  get progressPercent(): number {
    const estimate = this.issue?.estimate ?? 0;
    const spent = this.issue?.timeSpent ?? 0;
    if (!estimate || estimate <= 0) {
      return 0;
    }

    return Math.min(100, Math.round((spent / estimate) * 100));
  }

  get statusLabel(): string {
    return this.statusName || this.issue?.statusName || this.issue?.status || 'Backlog';
  }

  get descriptionPreview(): string {
    const raw = String(this.issue?.description ?? '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
    return raw || 'No description yet';
  }

  openIssueModal(issueId: string) {
    this._projectService.loadIssue(issueId).subscribe({
      next: () => {
        this._modalService.create({
          nzContent: IssueModalComponent,
          nzWidth: 1040,
          nzClosable: false,
          nzFooter: null,
          nzComponentParams: {
            issue$: this._projectQuery.issueById$(issueId)
          }
        });
      },
      error: (error) => {
        this._notification.error(
          error?.status === 404 ? 'Задача не найдена' : 'Не удалось открыть задачу',
          getApiErrorMessage(error, 'Проверьте доступ к задаче и повторите попытку.')
        );
      }
    });
  }
}
