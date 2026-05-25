import { Component, Input, OnChanges } from '@angular/core';
import { IssueType, JIssue } from '@trungk18/interface/issue';
import { IssueUtil } from '@trungk18/project/utils/issue';

@Component({
  selector: 'issue-type',
  templateUrl: './issue-type.component.html',
  styleUrls: ['./issue-type.component.scss']
})
export class IssueTypeComponent implements OnChanges {
  @Input() issue: JIssue;

  get selectedIssueTypeIcon(): string {
    return IssueUtil.getIssueTypeIcon(this.issue.type);
  }
  label = '';

  ngOnChanges(): void {
    this.label = this.issue?.type?.toUpperCase?.() || '';
  }
}
