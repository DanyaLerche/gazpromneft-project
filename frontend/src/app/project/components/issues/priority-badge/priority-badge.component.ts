import { Component, Input, OnChanges } from '@angular/core';
import { IssuePriority } from '@trungk18/interface/issue';
import { IssuePriorityIcon } from '@trungk18/interface/issue-priority-icon';
import { IssueUtil } from '@trungk18/project/utils/issue';

@Component({
  selector: 'priority-badge',
  templateUrl: './priority-badge.component.html',
  styleUrls: ['./priority-badge.component.scss']
})
export class PriorityBadgeComponent implements OnChanges {
  @Input() priority: IssuePriority;

  icon: IssuePriorityIcon;

  ngOnChanges(): void {
    this.icon = IssueUtil.getIssuePriorityIcon(this.priority);
  }
}
