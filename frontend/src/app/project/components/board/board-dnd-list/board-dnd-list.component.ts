import { CdkDragDrop } from '@angular/cdk/drag-drop';
import { Component, Input, OnInit } from '@angular/core';
import { JIssue } from '@trungk18/interface/issue';
import { JStatus } from '@trungk18/interface/status';
import { ProjectService } from '@trungk18/project/state/project/project.service';
import { Observable } from 'rxjs';
import { untilDestroyed, UntilDestroy } from '@ngneat/until-destroy';

@Component({
  selector: 'kanban-column',
  templateUrl: './board-dnd-list.component.html',
  styleUrls: ['./board-dnd-list.component.scss']
})
@UntilDestroy()
export class BoardDndListComponent implements OnInit {
  @Input() status: JStatus;
  @Input() issues$: Observable<JIssue[]>;

  issues: JIssue[] = [];

  get issuesCount(): number {
    return this.issues.length;
  }

  constructor(private _projectService: ProjectService) {}

  ngOnInit(): void {
    this.issues$.pipe(untilDestroyed(this)).subscribe((issues) => {
      this.issues = issues;
    });
  }

  drop(event: CdkDragDrop<JIssue[]>) {
    if (event.previousContainer === event.container) {
      return;
    }

    this._projectService.updateIssue({
      id: event.item.data.id,
      statusId: this.status.id,
      status: this.status.name
    });
  }

  trackByIssueId(_index: number, issue: JIssue): string {
    return issue.id;
  }
}
