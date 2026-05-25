import { Component, Input, OnChanges, OnInit, SimpleChanges } from '@angular/core';
import { UntilDestroy } from '@ngneat/until-destroy';
import { JIssue } from '@trungk18/interface/issue';
import { JUser } from '@trungk18/interface/user';
import { ProjectService } from '@trungk18/project/state/project/project.service';

@Component({
  selector: 'issue-assignees',
  templateUrl: './issue-assignees.component.html',
  styleUrls: ['./issue-assignees.component.scss']
})
@UntilDestroy()
export class IssueAssigneesComponent implements OnInit, OnChanges {
  @Input() issue: JIssue;
  @Input() users: JUser[];
  assignee: JUser;
  pendingAssigneeId: string | null = null;

  constructor(private _projectService: ProjectService) {}

  ngOnInit(): void {
    this.syncAssignee();
  }

  ngOnChanges(_changes: SimpleChanges) {
    this.syncAssignee();
  }

  removeUser(userId: string) {
    this.pendingAssigneeId = null;
    this._projectService.updateIssue({
      id: this.issue.id,
      assigneeId: null,
      userIds: []
    });
  }

  addUserToIssue(user: JUser) {
    this.pendingAssigneeId = null;
    this._projectService.updateIssue({
      id: this.issue.id,
      assigneeId: user.id,
      userIds: [user.id]
    });
  }

  isUserSelected(user: JUser): boolean {
    return this.issue.assigneeId === user.id;
  }

  selectAssignee(userId: string | null) {
    const user = this.users?.find((option) => option.id === userId);
    if (!user || this.isUserSelected(user)) {
      this.pendingAssigneeId = null;
      return;
    }

    this.addUserToIssue(user);
  }

  private syncAssignee() {
    this.assignee = this.users?.find((user) => user.id === this.issue?.assigneeId);
  }
}
