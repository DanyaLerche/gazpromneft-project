import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, NgModule, Output } from '@angular/core';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'outline' | 'destructive';
type ButtonSize = 'sm' | 'md' | 'lg';

@Component({
  selector: 'app-shell',
  template: `
    <div class="app-shell" [ngClass]="className">
      <aside class="app-shell__sidebar">
        <ng-content select="[app-shell-sidebar]"></ng-content>
      </aside>
      <div class="app-shell__main">
        <header class="app-shell__header">
          <ng-content select="[app-shell-header]"></ng-content>
        </header>
        <div class="app-shell__content">
          <ng-content></ng-content>
        </div>
      </div>
    </div>
  `
})
export class AppShellComponent {
  @Input() className = '';
}

@Component({
  selector: 'app-page',
  template: `<div class="app-page" [ngClass]="className"><ng-content></ng-content></div>`
})
export class AppPageComponent {
  @Input() className = '';
}

@Component({
  selector: 'app-section',
  template: `<section class="app-section" [ngClass]="className"><ng-content></ng-content></section>`
})
export class AppSectionComponent {
  @Input() className = '';
}

@Component({
  selector: 'app-toolbar',
  template: `<div class="app-toolbar" [ngClass]="className"><ng-content></ng-content></div>`
})
export class AppToolbarComponent {
  @Input() className = '';
}

@Component({
  selector: 'app-card',
  template: `<section [ngClass]="classes"><ng-content></ng-content></section>`
})
export class AppCardComponent {
  @Input() compact = false;
  @Input() danger = false;
  @Input() className = '';

  get classes(): string[] {
    return [
      'app-card',
      this.compact ? 'app-card--compact' : '',
      this.danger ? 'app-card--danger' : '',
      this.className
    ].filter(Boolean);
  }
}

@Component({
  selector: 'app-button',
  template: `
    <button
      [type]="type"
      [disabled]="disabled || loading"
      [attr.aria-busy]="loading"
      [attr.aria-label]="ariaLabel || null"
      [ngClass]="classes">
      <span class="app-button__loader" *ngIf="loading">···</span>
      <ng-content></ng-content>
    </button>
  `
})
export class AppButtonComponent {
  @Input() type: 'button' | 'submit' | 'reset' = 'button';
  @Input() variant: ButtonVariant = 'primary';
  @Input() size: ButtonSize = 'md';
  @Input() disabled = false;
  @Input() loading = false;
  @Input() className = '';
  @Input() ariaLabel = '';

  get classes(): string[] {
    return [
      'app-button',
      `app-button--${this.variant}`,
      this.size === 'md' ? '' : `app-button--${this.size}`,
      this.className
    ].filter(Boolean);
  }
}

@Component({
  selector: 'app-input',
  template: `
    <label [ngClass]="['app-input-field', className]">
      <span class="app-label" *ngIf="label">{{ label }}</span>
      <input
        class="app-input"
        [class.app-input--invalid]="invalid"
        [type]="type"
        [value]="value"
        [placeholder]="placeholder"
        [disabled]="disabled"
        [required]="required"
        [attr.aria-label]="ariaLabel || label || null"
        (input)="onInput($event)" />
      <span class="app-helper-text" *ngIf="hint && !error">{{ hint }}</span>
      <span class="app-error-text" *ngIf="error">{{ error }}</span>
    </label>
  `
})
export class AppInputComponent {
  @Input() label = '';
  @Input() value = '';
  @Input() type = 'text';
  @Input() placeholder = '';
  @Input() hint = '';
  @Input() error = '';
  @Input() required = false;
  @Input() disabled = false;
  @Input() invalid = false;
  @Input() className = '';
  @Input() ariaLabel = '';

  @Output() valueChange = new EventEmitter<string>();

  onInput(event: Event): void {
    const target = event.target as HTMLInputElement;
    this.valueChange.emit(target.value);
  }
}

@Component({
  selector: 'app-badge',
  template: `<span [ngClass]="classes"><ng-content></ng-content></span>`
})
export class AppBadgeComponent {
  @Input() tone: 'neutral' | 'primary' | 'success' | 'warning' | 'danger' = 'neutral';
  @Input() className = '';

  get classes(): string[] {
    return ['app-badge', `app-badge--${this.tone}`, this.className].filter(Boolean);
  }
}

@Component({
  selector: 'app-avatar',
  template: `
    <div class="app-avatar" [style.width.px]="size" [style.height.px]="size" [ngClass]="className">
      <img *ngIf="src; else fallback" [src]="src" [alt]="name || 'Avatar'" />
      <ng-template #fallback>{{ initials }}</ng-template>
    </div>
  `
})
export class AppAvatarComponent {
  @Input() src = '';
  @Input() name = '';
  @Input() size = 36;
  @Input() className = '';

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
}

@Component({
  selector: 'app-table',
  template: `<div class="app-table" [ngClass]="className"><ng-content></ng-content></div>`
})
export class AppTableComponent {
  @Input() className = '';
}

export interface AppTabItem {
  id: string;
  label: string;
}

@Component({
  selector: 'app-tabs',
  template: `
    <div class="app-tabs" [ngClass]="className" role="tablist">
      <button
        *ngFor="let item of items; trackBy: trackById"
        type="button"
        role="tab"
        [attr.aria-selected]="item.id === activeId"
        [ngClass]="['app-tabs__item', item.id === activeId ? 'app-tabs__item--active' : '']"
        (click)="select(item.id)">
        {{ item.label }}
      </button>
    </div>
  `
})
export class AppTabsComponent {
  @Input() items: AppTabItem[] = [];
  @Input() activeId = '';
  @Input() className = '';

  @Output() activeIdChange = new EventEmitter<string>();

  trackById(_: number, item: AppTabItem): string {
    return item.id;
  }

  select(id: string): void {
    this.activeIdChange.emit(id);
  }
}

@Component({
  selector: 'app-empty-state',
  template: `
    <div class="app-empty-state" [ngClass]="className">
      <div class="app-empty-state__icon" *ngIf="icon">{{ icon }}</div>
      <div class="app-empty-state__title">{{ title }}</div>
      <p class="app-empty-state__description" *ngIf="description">{{ description }}</p>
      <ng-content></ng-content>
    </div>
  `
})
export class AppEmptyStateComponent {
  @Input() icon = '•';
  @Input() title = '';
  @Input() description = '';
  @Input() className = '';
}

@Component({
  selector: 'app-modal',
  template: `
    <div class="app-modal-backdrop" [ngClass]="backdropClassName">
      <div class="app-modal" [ngClass]="className">
        <div class="app-modal__header" *ngIf="title || description">
          <div>
            <h2 class="app-modal__title" *ngIf="title">{{ title }}</h2>
            <p class="app-modal__description" *ngIf="description">{{ description }}</p>
          </div>
          <ng-content select="[app-modal-close]"></ng-content>
        </div>
        <ng-content></ng-content>
        <div class="app-modal__footer">
          <ng-content select="[app-modal-footer]"></ng-content>
        </div>
      </div>
    </div>
  `
})
export class AppModalComponent {
  @Input() title = '';
  @Input() description = '';
  @Input() className = '';
  @Input() backdropClassName = '';
}

const APP_UI_PRIMITIVES = [
  AppShellComponent,
  AppPageComponent,
  AppSectionComponent,
  AppToolbarComponent,
  AppCardComponent,
  AppButtonComponent,
  AppInputComponent,
  AppBadgeComponent,
  AppAvatarComponent,
  AppTableComponent,
  AppTabsComponent,
  AppEmptyStateComponent,
  AppModalComponent
];

@NgModule({
  declarations: APP_UI_PRIMITIVES,
  imports: [CommonModule],
  exports: APP_UI_PRIMITIVES
})
export class AppUiModule {}
