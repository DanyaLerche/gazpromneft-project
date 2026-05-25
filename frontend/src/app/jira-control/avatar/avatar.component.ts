import { Component, Input } from '@angular/core';

@Component({
  selector: 'j-avatar',
  templateUrl: './avatar.component.html',
  styleUrls: ['./avatar.component.scss']
})
export class AvatarComponent {
  @Input() avatarUrl: string;
  @Input() size = 12;
  @Input() name = '';
  @Input() rounded = true;
  @Input() className = '';

  get hasAvatar(): boolean {
    return !!this.avatarUrl?.trim();
  }

  get initials(): string {
    const parts = this.name
      .trim()
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2);

    if (!parts.length) {
      return '?';
    }

    return parts.map((part) => part.charAt(0).toUpperCase()).join('');
  }

  get style() {
    return {
      width: `${this.size}px`,
      height: `${this.size}px`,
      'background-image': this.hasAvatar ? `url('${this.avatarUrl}')` : 'none',
      'border-radius': this.rounded ? '100%' : '3px'
    };
  }
}
