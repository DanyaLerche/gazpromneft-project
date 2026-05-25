import { ProjectState, ProjectStore } from './project.store';
import { Injectable } from '@angular/core';
import { Query } from '@datorama/akita';
import { IssuePriority, JIssue } from '@trungk18/interface/issue';
import { isAdminProjectRole, ProjectRole } from '@trungk18/interface/role';
import { map, delay } from 'rxjs/operators';
import { Observable } from 'rxjs';
import { JStatus } from '@trungk18/interface/status';
@Injectable({
  providedIn: 'root'
})
export class ProjectQuery extends Query<ProjectState> {
  isLoading$ = this.selectLoading();
  error$ = this.selectError();
  all$ = this.select();
  project$ = this.select();
  issues$ = this.select('issues');
  users$ = this.select('users');
  statuses$ = this.select('statuses');
  criticalities$ = this.select('criticalities');
  currentUserRole$ = this.select('currentUserRole');
  newEmployeeMode$ = this.select('newEmployeeMode');
  isCurrentUserProjectAdmin$ = this.currentUserRole$.pipe(map((role) => isAdminProjectRole(role)));

  constructor(protected store: ProjectStore) {
    super(store);
  }

  get currentUserRole(): ProjectRole | null {
    return this.getValue().currentUserRole;
  }

  get isCurrentUserProjectAdmin(): boolean {
    return isAdminProjectRole(this.currentUserRole);
  }

  lastIssuePosition = (statusId: string): number => {
    const raw = this.store.getValue();
    const issuesByStatus = raw.issues.filter((x) => x.statusId === statusId);
    return issuesByStatus.length;
  };

  issueByStatusSorted$ = (statusId: string): Observable<JIssue[]> =>
    this.issues$.pipe(
      map((issues) =>
        issues
          .filter((x) => x.statusId === statusId)
          .sort((left, right) => this.compareBoardIssues(left, right))
      )
    );

  issueById$(issueId: string) {
    return this.issues$.pipe(
      delay(500),
      map((issues) => issues.find((x) => x.id === issueId))
    );
  }

  statusById(statusId: string): JStatus | undefined {
    return this.store.getValue().statuses.find((status) => status.id === statusId);
  }

  criticalityById(criticalityId: string | null | undefined) {
    if (!criticalityId) {
      return undefined;
    }

    return this.store.getValue().criticalities.find((criticality) => criticality.id === criticalityId);
  }

  private compareBoardIssues(left: JIssue, right: JIssue): number {
    const priorityDiff = this.getPriorityWeight(right.priority) - this.getPriorityWeight(left.priority);
    if (priorityDiff !== 0) {
      return priorityDiff;
    }

    const dueDateDiff = this.compareDueDates(left.dueDate, right.dueDate);
    if (dueDateDiff !== 0) {
      return dueDateDiff;
    }

    return left.listPosition - right.listPosition;
  }

  private compareDueDates(left: string | null | undefined, right: string | null | undefined): number {
    if (!left && !right) {
      return 0;
    }

    if (!left) {
      return 1;
    }

    if (!right) {
      return -1;
    }

    return new Date(left).getTime() - new Date(right).getTime();
  }

  private getPriorityWeight(priority: IssuePriority | string | null | undefined): number {
    switch (priority) {
      case IssuePriority.HIGHEST:
        return 5;
      case IssuePriority.HIGH:
        return 4;
      case IssuePriority.MEDIUM:
        return 3;
      case IssuePriority.LOW:
        return 2;
      case IssuePriority.LOWEST:
        return 1;
      default:
        return 0;
    }
  }
}
