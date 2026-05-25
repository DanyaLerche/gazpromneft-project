import { Component, Input } from '@angular/core';
import { JUser } from '@trungk18/interface/user';
import { UntypedFormControl } from '@angular/forms';

@Component({
  selector: 'issue-assignees-select',
  templateUrl: './issue-assignees-select.component.html',
  styleUrls: ['./issue-assignees-select.component.scss']
})
export class IssueAssigneesSelectComponent {
  @Input() control: UntypedFormControl;
  @Input() users: JUser[];
}
