import { Component, Input } from '@angular/core';
import { JUser } from '@trungk18/interface/user';

@Component({
  selector: 'user-avatar-group',
  templateUrl: './user-avatar-group.component.html',
  styleUrls: ['./user-avatar-group.component.scss']
})
export class UserAvatarGroupComponent {
  @Input() users: JUser[] = [];
  @Input() maxVisible = 3;

  get visibleUsers(): JUser[] {
    return this.users.slice(0, this.maxVisible);
  }

  get hiddenCount(): number {
    return Math.max(0, this.users.length - this.maxVisible);
  }
}
