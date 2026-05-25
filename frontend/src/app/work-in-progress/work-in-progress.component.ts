import { Component } from '@angular/core';
import {
  FocusConfig,
  FocusModeService
} from '@trungk18/core/services/focus-mode.service';

@Component({
  selector: 'work-in-progress',
  templateUrl: './work-in-progress.component.html',
  styleUrls: ['./work-in-progress.component.scss']
})
export class WorkInProgressComponent {
  constructor(public focusMode: FocusModeService) {}

  updateNumberConfig(
    field: keyof Pick<
      FocusConfig,
      'focusMinutes' | 'shortBreakMinutes' | 'longBreakMinutes' | 'sessionsBeforeLongBreak'
    >,
    event: Event
  ): void {
    const input = event.target as HTMLInputElement;
    const value = Number.parseInt(input.value, 10);
    if (Number.isNaN(value)) {
      return;
    }
    const normalizedValue = this.focusMode.updateNumberConfig(field, value);
    input.value = String(normalizedValue);
  }

  async updateBooleanConfig(
    field: keyof Pick<
      FocusConfig,
      'autoStartBreaks' | 'autoStartFocus' | 'soundEnabled' | 'browserNotificationsEnabled'
    >,
    event: Event
  ): Promise<void> {
    const input = event.target as HTMLInputElement;
    const enabled = await this.focusMode.updateBooleanConfig(field, input.checked);
    input.checked = enabled;
  }

  get notificationBlocked(): boolean {
    return (
      this.focusMode.state.notificationPermission === 'denied' &&
      !this.focusMode.state.config.browserNotificationsEnabled
    );
  }

  get notificationsUnsupported(): boolean {
    return this.focusMode.state.notificationPermission === 'unsupported';
  }
}
