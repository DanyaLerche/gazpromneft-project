import { Component, EventEmitter, Input, Output } from '@angular/core';

@Component({
  selector: 'top-navbar',
  templateUrl: './top-navbar.component.html',
  styleUrls: ['./top-navbar.component.scss']
})
export class TopNavbarComponent {
  @Input() projectName = '';
  @Input() projectKey = '';
  @Input() searchQuery = '';
  @Input() showBoardActions = false;
  @Input() loading = false;

  @Output() searchChanged = new EventEmitter<string>();
  @Output() createIssue = new EventEmitter<void>();
  @Output() menuClick = new EventEmitter<void>();

  onSearchInput(event: Event): void {
    const value = String((event.target as HTMLInputElement)?.value ?? '');
    this.searchChanged.emit(value);
  }
}
