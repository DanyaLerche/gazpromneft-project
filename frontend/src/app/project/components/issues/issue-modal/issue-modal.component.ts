import { Component, Input } from '@angular/core';
import { Router } from '@angular/router';
import { JIssue } from '@trungk18/interface/issue';
import { ProjectService } from '@trungk18/project/state/project/project.service';
import { NzModalRef } from 'ng-zorro-antd/modal';
import { Observable } from 'rxjs';
import { DeleteIssueModel } from '@trungk18/interface/ui-model/delete-issue-model';
import { NzNotificationService } from 'ng-zorro-antd/notification';
import { getApiErrorMessage } from '@trungk18/core/utils/api-error';

@Component({
  selector: 'issue-modal',
  templateUrl: './issue-modal.component.html',
  styleUrls: ['./issue-modal.component.scss']
})
export class IssueModalComponent {
  @Input() issue$: Observable<JIssue>;

  constructor(
    private _modal: NzModalRef,
    private _router: Router,
    private _projectService: ProjectService,
    private _notification: NzNotificationService
  ) {}

  closeModal() {
    this._modal.close();
  }

  openIssuePage(issueId: string) {
    this.closeModal();
    const projectId = this._projectService.currentProjectId;
    if (!projectId) {
      return;
    }
    this._router.navigate(['/projects', projectId, 'issue', issueId]);
  }

  deleteIssue({ issueId, deleteModalRef }: DeleteIssueModel) {
    this._projectService.deleteIssue(issueId).subscribe({
      next: () => {
        deleteModalRef.close();
        this.closeModal();
      },
      error: (error) => {
        this._notification.error(
          error?.status === 403
            ? 'Нет прав на удаление задачи'
            : error?.status === 404
              ? 'Задача не найдена'
              : 'Не удалось удалить задачу',
          getApiErrorMessage(error, 'Повторите попытку позже.')
        );
      }
    });
  }
}
