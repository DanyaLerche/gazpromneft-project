import { Component, Input } from '@angular/core';

@Component({
  selector: 'status-badge',
  templateUrl: './status-badge.component.html',
  styleUrls: ['./status-badge.component.scss']
})
export class StatusBadgeComponent {
  @Input() status = '';

  get tone(): 'success' | 'warning' | 'neutral' {
    const normalized = this.status.toLowerCase();
    if (normalized.includes('done') || normalized.includes('выполн')) {
      return 'success';
    }
    if (normalized.includes('progress') || normalized.includes('work') || normalized.includes('проц')) {
      return 'warning';
    }
    return 'neutral';
  }
}
