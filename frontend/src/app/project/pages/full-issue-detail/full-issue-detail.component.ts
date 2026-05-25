import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { ProjectConst } from '@trungk18/project/config/const';
import { ProjectQuery } from '@trungk18/project/state/project/project.query';
import { JProject } from '@trungk18/interface/project';
import { untilDestroyed, UntilDestroy } from '@ngneat/until-destroy';
import { Observable } from 'rxjs';
import { JIssue } from '@trungk18/interface/issue';
import { ProjectService } from '@trungk18/project/state/project/project.service';
import { DeleteIssueModel } from '@trungk18/interface/ui-model/delete-issue-model';
import { getApiErrorMessage } from '@trungk18/core/utils/api-error';
import { NzNotificationService } from 'ng-zorro-antd/notification';

@Component({
  selector: 'full-issue-detail',
  templateUrl: './full-issue-detail.component.html',
  styleUrls: ['./full-issue-detail.component.scss']
})
@UntilDestroy()
export class FullIssueDetailComponent implements OnInit {
  project: JProject;
  issueById$: Observable<JIssue>;
  issueId: string;
  isLoading = true;
  issueErrorTitle = '';
  issueErrorMessage = '';

  get breadcrumbs(): string[] {
    return [ProjectConst.Проекты, this.project?.name, 'Issues', this.issueId];
  }

  constructor(
    private _router: Router,
    private _route: ActivatedRoute,
    private _projectQuery: ProjectQuery,
    private _projectService: ProjectService,
    private _notification: NzNotificationService
  ) {}

  ngOnInit(): void {
    this.getIssue();
    this._projectQuery.all$.pipe(untilDestroyed(this)).subscribe((project) => {
      this.project = project;
    });
  }

  deleteIssue({ issueId, deleteModalRef }: DeleteIssueModel) {
    this._projectService.deleteIssue(issueId).subscribe({
      next: () => {
        deleteModalRef.close();
        this.backHome();
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

  get hasIssueError(): boolean {
    return !!this.issueErrorMessage;
  }

  private getIssue() {
    this.issueId = this._route.snapshot.paramMap.get(ProjectConst.IssueId);
    if (!this.issueId) {
      this.backHome();
      return;
    }
    this.issueById$ = this._projectQuery.issueById$(this.issueId);
    this.isLoading = true;
    this.issueErrorTitle = '';
    this.issueErrorMessage = '';

    this._projectService.loadIssue(this.issueId).subscribe({
      next: () => {
        this.isLoading = false;
      },
      error: (error) => {
        this.isLoading = false;
        this.issueErrorTitle =
          error?.status === 404
            ? 'Задача не найдена'
            : error?.status === 403
              ? 'Нет доступа к задаче'
              : 'Не удалось загрузить задачу';
        this.issueErrorMessage =
          error?.status === 404
            ? 'Проверьте идентификатор задачи или вернитесь на доску проекта.'
            : error?.status === 403
              ? 'У текущего пользователя нет доступа к этой задаче.'
              : getApiErrorMessage(error, 'Не удалось загрузить карточку задачи.');
      }
    });
  }

  backHome() {
    const projectId =
      this.project?.id ?? this._route.parent?.snapshot.paramMap.get(ProjectConst.ProjectId);

    if (!projectId) {
      this._router.navigate(['/']);
      return;
    }

    this._router.navigate(['/projects', projectId, 'board']);
  }
}
