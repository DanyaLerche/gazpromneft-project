import { Component, Input, OnChanges, OnInit } from '@angular/core';
import { JIssue } from '@trungk18/interface/issue';
import { JStatus } from '@trungk18/interface/status';
import { ProjectService } from '@trungk18/project/state/project/project.service';
import { ProjectQuery } from '@trungk18/project/state/project/project.query';
import { untilDestroyed, UntilDestroy } from '@ngneat/until-destroy';

@Component({
  selector: 'issue-status',
  templateUrl: './issue-status.component.html',
  styleUrls: ['./issue-status.component.scss']
})
@UntilDestroy()
export class IssueStatusComponent implements OnInit, OnChanges {
  @Input() issue: JIssue;
  issueStatuses: JStatus[] = [];
  currentStatus: JStatus;

  constructor(private _projectService: ProjectService, private _projectQuery: ProjectQuery) {}

  ngOnInit(): void {
    this._projectQuery.statuses$
      .pipe(untilDestroyed(this))
      .subscribe((statuses) => {
        this.issueStatuses = statuses;
        this.syncCurrentStatus();
      });
  }

  ngOnChanges(): void {
    this.syncCurrentStatus();
  }

  updateIssue(status: JStatus) {
    const newPosition = this._projectQuery.lastIssuePosition(status.id);
    this._projectService.updateIssue({
      id: this.issue.id,
      statusId: status.id,
      status: status.name,
      listPosition: newPosition + 1
    });
  }

  updateIssueById(statusId: string | null) {
    const nextStatus = this.issueStatuses.find((status) => status.id === statusId);
    if (!nextStatus || this.isStatusSelected(nextStatus)) {
      return;
    }

    this.updateIssue(nextStatus);
  }

  isStatusSelected(status: JStatus) {
    return this.issue.statusId === status.id;
  }

  getClassName(status: JStatus | undefined): string {
    if (!status) {
      return 'btn-secondary uppercase text-textMedium text-13';
    }

    switch (status.category) {
      case 'done':
        return 'btn-success uppercase text-textMedium text-13';
      case 'in_progress':
        return 'btn-primary uppercase text-textMedium text-13';
      default:
        return 'btn-secondary uppercase text-textMedium text-13';
    }
  }

  private syncCurrentStatus() {
    this.currentStatus = this.issueStatuses.find((status) => status.id === this.issue?.statusId);
  }
}
