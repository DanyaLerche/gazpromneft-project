import { Injectable } from '@angular/core';

export type FocusPhase = 'focus' | 'shortBreak' | 'longBreak';

export interface FocusConfig {
  focusMinutes: number;
  shortBreakMinutes: number;
  longBreakMinutes: number;
  sessionsBeforeLongBreak: number;
  autoStartBreaks: boolean;
  autoStartFocus: boolean;
  soundEnabled: boolean;
  browserNotificationsEnabled: boolean;
}

interface FocusModeSnapshot {
  currentPhase: FocusPhase;
  remainingSeconds: number;
  isRunning: boolean;
  completedFocusSessions: number;
  focusSecondsToday: number;
  lastTickEpochMs: number;
  dayStamp: string;
  config: FocusConfig;
}

export interface FocusModeState {
  currentPhase: FocusPhase;
  remainingSeconds: number;
  isRunning: boolean;
  completedFocusSessions: number;
  focusSecondsToday: number;
  progressPercent: number;
  phaseLabel: string;
  timerLabel: string;
  focusMinutesToday: number;
  sessionsUntilLongBreak: number;
  config: FocusConfig;
  notificationPermission: NotificationPermission | 'unsupported';
}

@Injectable({
  providedIn: 'root'
})
export class FocusModeService {
  readonly phases: Array<{ id: FocusPhase; label: string }> = [
    { id: 'focus', label: 'Фокус' },
    { id: 'shortBreak', label: 'Короткий перерыв' },
    { id: 'longBreak', label: 'Длинный перерыв' }
  ];

  readonly configLimits = {
    focusMinutes: { min: 10, max: 90 },
    shortBreakMinutes: { min: 3, max: 30 },
    longBreakMinutes: { min: 10, max: 60 },
    sessionsBeforeLongBreak: { min: 2, max: 8 }
  };

  currentPhase: FocusPhase = 'focus';
  remainingSeconds = 25 * 60;
  isRunning = false;
  completedFocusSessions = 0;
  focusSecondsToday = 0;
  lastTickEpochMs = Date.now();
  config: FocusConfig = {
    focusMinutes: 25,
    shortBreakMinutes: 5,
    longBreakMinutes: 15,
    sessionsBeforeLongBreak: 4,
    autoStartBreaks: true,
    autoStartFocus: false,
    soundEnabled: true,
    browserNotificationsEnabled: false
  };

  private readonly storageKey = 'focus-mode.v2';
  private timerId: ReturnType<typeof setInterval> | null = null;
  private audioContext: AudioContext | null = null;

  constructor() {
    this.restoreFromStorage();
  }

  get state(): FocusModeState {
    return {
      currentPhase: this.currentPhase,
      remainingSeconds: this.remainingSeconds,
      isRunning: this.isRunning,
      completedFocusSessions: this.completedFocusSessions,
      focusSecondsToday: this.focusSecondsToday,
      progressPercent: this.progressPercent,
      phaseLabel: this.phaseLabel,
      timerLabel: this.timerLabel,
      focusMinutesToday: this.focusMinutesToday,
      sessionsUntilLongBreak: this.sessionsUntilLongBreak,
      config: { ...this.config },
      notificationPermission: this.notificationPermission
    };
  }

  get phaseLabel(): string {
    const active = this.phases.find((phase) => phase.id === this.currentPhase);
    return active?.label ?? 'Фокус';
  }

  get timerLabel(): string {
    const minutes = Math.floor(this.remainingSeconds / 60);
    const seconds = this.remainingSeconds % 60;
    return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  }

  get progressPercent(): number {
    const totalSeconds = this.getPhaseDurationSeconds(this.currentPhase);
    if (totalSeconds <= 0) {
      return 0;
    }
    return Math.min(100, Math.max(0, Math.round(((totalSeconds - this.remainingSeconds) / totalSeconds) * 100)));
  }

  get focusMinutesToday(): number {
    return Math.floor(this.focusSecondsToday / 60);
  }

  get sessionsUntilLongBreak(): number {
    const remainder = this.completedFocusSessions % this.config.sessionsBeforeLongBreak;
    return remainder === 0
      ? this.config.sessionsBeforeLongBreak
      : this.config.sessionsBeforeLongBreak - remainder;
  }

  get notificationPermission(): NotificationPermission | 'unsupported' {
    if (typeof Notification === 'undefined') {
      return 'unsupported';
    }
    return Notification.permission;
  }

  selectPhase(phase: FocusPhase): void {
    this.pauseTimer();
    this.currentPhase = phase;
    this.remainingSeconds = this.getPhaseDurationSeconds(phase);
    this.persistState();
  }

  toggleTimer(): void {
    if (this.isRunning) {
      this.pauseTimer();
      return;
    }
    this.startTimer();
  }

  resetCurrentPhase(): void {
    this.pauseTimer();
    this.remainingSeconds = this.getPhaseDurationSeconds(this.currentPhase);
    this.persistState();
  }

  resetProgress(): void {
    this.pauseTimer();
    this.currentPhase = 'focus';
    this.remainingSeconds = this.getPhaseDurationSeconds('focus');
    this.completedFocusSessions = 0;
    this.focusSecondsToday = 0;
    this.persistState();
  }

  updateNumberConfig(field: keyof Pick<FocusConfig, 'focusMinutes' | 'shortBreakMinutes' | 'longBreakMinutes' | 'sessionsBeforeLongBreak'>, value: number): number {
    const limits = this.configLimits[field];
    const normalizedValue = Math.min(limits.max, Math.max(limits.min, Math.floor(value)));
    this.config = {
      ...this.config,
      [field]: normalizedValue
    };

    if (!this.isRunning) {
      this.remainingSeconds = this.getPhaseDurationSeconds(this.currentPhase);
    }
    this.persistState();
    return normalizedValue;
  }

  async updateBooleanConfig(field: keyof Pick<FocusConfig, 'autoStartBreaks' | 'autoStartFocus' | 'soundEnabled' | 'browserNotificationsEnabled'>, enabled: boolean): Promise<boolean> {
    if (field === 'browserNotificationsEnabled' && enabled) {
      const granted = await this.ensureNotificationPermission();
      this.config = {
        ...this.config,
        browserNotificationsEnabled: granted
      };
      this.persistState();
      return granted;
    }

    this.config = {
      ...this.config,
      [field]: enabled
    };
    this.persistState();
    return enabled;
  }

  private startTimer(): void {
    if (this.isRunning) {
      return;
    }
    this.isRunning = true;
    this.lastTickEpochMs = Date.now();
    this.startTicker();
    this.persistState();
  }

  private pauseTimer(): void {
    this.isRunning = false;
    this.stopTicker();
    this.persistState();
  }

  private startTicker(): void {
    if (this.timerId) {
      return;
    }

    this.timerId = setInterval(() => {
      if (!this.isRunning) {
        return;
      }

      const now = Date.now();
      const elapsedSeconds = Math.max(0, Math.floor((now - this.lastTickEpochMs) / 1000));
      if (elapsedSeconds <= 0) {
        return;
      }

      this.lastTickEpochMs = now;
      this.consumeElapsedSeconds(elapsedSeconds);
      this.persistState();
    }, 1000);
  }

  private stopTicker(): void {
    if (!this.timerId) {
      return;
    }
    clearInterval(this.timerId);
    this.timerId = null;
  }

  private consumeElapsedSeconds(seconds: number): void {
    let secondsToConsume = seconds;

    while (secondsToConsume > 0) {
      const step = Math.min(secondsToConsume, this.remainingSeconds);
      this.remainingSeconds -= step;

      if (this.currentPhase === 'focus') {
        this.focusSecondsToday += step;
      }

      secondsToConsume -= step;

      if (this.remainingSeconds === 0) {
        const shouldContinue = this.advancePhaseAfterFinish();
        if (!shouldContinue) {
          break;
        }
      }
    }
  }

  private advancePhaseAfterFinish(): boolean {
    const previousPhase = this.currentPhase;

    if (this.currentPhase === 'focus') {
      this.completedFocusSessions += 1;
      const longBreakDue = this.completedFocusSessions % this.config.sessionsBeforeLongBreak === 0;
      this.currentPhase = longBreakDue ? 'longBreak' : 'shortBreak';
      this.remainingSeconds = this.getPhaseDurationSeconds(this.currentPhase);
      this.handlePhaseSwitchSignal(previousPhase, this.currentPhase);

      if (!this.config.autoStartBreaks) {
        this.isRunning = false;
        this.stopTicker();
        return false;
      }
      return true;
    }

    this.currentPhase = 'focus';
    this.remainingSeconds = this.getPhaseDurationSeconds('focus');
    this.handlePhaseSwitchSignal(previousPhase, this.currentPhase);

    if (!this.config.autoStartFocus) {
      this.isRunning = false;
      this.stopTicker();
      return false;
    }
    return true;
  }

  private handlePhaseSwitchSignal(previousPhase: FocusPhase, nextPhase: FocusPhase): void {
    if (this.config.soundEnabled) {
      this.playSignal();
    }

    if (this.config.browserNotificationsEnabled) {
      this.sendBrowserNotification(previousPhase, nextPhase);
    }
  }

  private playSignal(): void {
    try {
      const ContextCtor = window.AudioContext || (window as any).webkitAudioContext;
      if (!ContextCtor) {
        return;
      }

      if (!this.audioContext) {
        this.audioContext = new ContextCtor();
      }

      if (this.audioContext.state === 'suspended') {
        this.audioContext.resume().catch(() => {});
      }

      const oscillator = this.audioContext.createOscillator();
      const gainNode = this.audioContext.createGain();
      oscillator.type = 'sine';
      oscillator.frequency.value = 880;
      gainNode.gain.value = 0.0001;
      oscillator.connect(gainNode);
      gainNode.connect(this.audioContext.destination);

      const now = this.audioContext.currentTime;
      gainNode.gain.exponentialRampToValueAtTime(0.12, now + 0.02);
      gainNode.gain.exponentialRampToValueAtTime(0.0001, now + 0.22);
      oscillator.start(now);
      oscillator.stop(now + 0.24);
    } catch {
      // Ignore sound errors silently.
    }
  }

  private sendBrowserNotification(previousPhase: FocusPhase, nextPhase: FocusPhase): void {
    if (typeof Notification === 'undefined' || Notification.permission !== 'granted') {
      return;
    }

    const title = previousPhase === 'focus'
      ? 'Фокус-сессия завершена'
      : 'Перерыв завершен';
    const body = previousPhase === 'focus'
      ? `Переход в режим: ${this.getPhaseLabel(nextPhase)}`
      : 'Время вернуться к фокус-сессии';

    new Notification(title, {
      body,
      tag: 'focus-mode-phase',
      renotify: true
    });
  }

  private async ensureNotificationPermission(): Promise<boolean> {
    if (typeof Notification === 'undefined') {
      return false;
    }
    if (Notification.permission === 'granted') {
      return true;
    }
    if (Notification.permission === 'denied') {
      return false;
    }

    try {
      const permission = await Notification.requestPermission();
      return permission === 'granted';
    } catch {
      return false;
    }
  }

  private getPhaseDurationSeconds(phase: FocusPhase): number {
    if (phase === 'focus') {
      return this.config.focusMinutes * 60;
    }
    if (phase === 'shortBreak') {
      return this.config.shortBreakMinutes * 60;
    }
    return this.config.longBreakMinutes * 60;
  }

  private getPhaseLabel(phase: FocusPhase): string {
    return this.phases.find((item) => item.id === phase)?.label ?? 'Фокус';
  }

  private restoreFromStorage(): void {
    const raw = localStorage.getItem(this.storageKey);
    const today = this.getDayStamp();

    if (!raw) {
      this.persistState();
      return;
    }

    try {
      const parsed = JSON.parse(raw) as Partial<FocusModeSnapshot>;
      const savedConfig: Partial<FocusConfig> = parsed.config ?? {};

      this.config = {
        focusMinutes: this.clampNumber(savedConfig.focusMinutes, this.configLimits.focusMinutes.min, this.configLimits.focusMinutes.max, 25),
        shortBreakMinutes: this.clampNumber(savedConfig.shortBreakMinutes, this.configLimits.shortBreakMinutes.min, this.configLimits.shortBreakMinutes.max, 5),
        longBreakMinutes: this.clampNumber(savedConfig.longBreakMinutes, this.configLimits.longBreakMinutes.min, this.configLimits.longBreakMinutes.max, 15),
        sessionsBeforeLongBreak: this.clampNumber(savedConfig.sessionsBeforeLongBreak, this.configLimits.sessionsBeforeLongBreak.min, this.configLimits.sessionsBeforeLongBreak.max, 4),
        autoStartBreaks: this.toBoolean(savedConfig.autoStartBreaks, true),
        autoStartFocus: this.toBoolean(savedConfig.autoStartFocus, false),
        soundEnabled: this.toBoolean(savedConfig.soundEnabled, true),
        browserNotificationsEnabled: this.toBoolean(savedConfig.browserNotificationsEnabled, false)
      };

      const restoredPhase = this.normalizePhase(parsed.currentPhase);
      this.currentPhase = restoredPhase;
      this.remainingSeconds = this.clampNumber(
        parsed.remainingSeconds,
        0,
        this.getPhaseDurationSeconds(restoredPhase),
        this.getPhaseDurationSeconds(restoredPhase)
      );
      this.completedFocusSessions = this.clampNumber(parsed.completedFocusSessions, 0, Number.MAX_SAFE_INTEGER, 0);
      this.focusSecondsToday = parsed.dayStamp === today
        ? this.clampNumber(parsed.focusSecondsToday, 0, Number.MAX_SAFE_INTEGER, 0)
        : 0;

      const wasRunning = Boolean(parsed.isRunning);
      this.lastTickEpochMs = this.clampNumber(parsed.lastTickEpochMs, 0, Number.MAX_SAFE_INTEGER, Date.now());

      if (wasRunning) {
        this.isRunning = true;
        const elapsed = Math.max(0, Math.floor((Date.now() - this.lastTickEpochMs) / 1000));
        if (elapsed > 0) {
          this.consumeElapsedSeconds(elapsed);
        }
        this.lastTickEpochMs = Date.now();
        if (this.isRunning) {
          this.startTicker();
        }
      }
    } catch {
      this.resetProgress();
      return;
    }

    this.persistState();
  }

  private persistState(): void {
    const snapshot: FocusModeSnapshot = {
      currentPhase: this.currentPhase,
      remainingSeconds: this.remainingSeconds,
      isRunning: this.isRunning,
      completedFocusSessions: this.completedFocusSessions,
      focusSecondsToday: this.focusSecondsToday,
      lastTickEpochMs: this.lastTickEpochMs,
      dayStamp: this.getDayStamp(),
      config: this.config
    };

    localStorage.setItem(this.storageKey, JSON.stringify(snapshot));
  }

  private getDayStamp(): string {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  private normalizePhase(value: unknown): FocusPhase {
    return value === 'shortBreak' || value === 'longBreak' ? value : 'focus';
  }

  private clampNumber(value: unknown, min: number, max: number, fallback: number): number {
    if (typeof value !== 'number' || !Number.isFinite(value)) {
      return fallback;
    }
    return Math.min(max, Math.max(min, Math.floor(value)));
  }

  private toBoolean(value: unknown, fallback: boolean): boolean {
    if (typeof value === 'boolean') {
      return value;
    }
    return fallback;
  }
}
