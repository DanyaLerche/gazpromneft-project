import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { UserProfilePreferencesService } from '@trungk18/core/services/user-profile-preferences.service';
import { JUser } from '@trungk18/interface/user';
import { finalize } from 'rxjs/operators';

@Component({
  selector: 'j-user-profile-popover',
  templateUrl: './user-profile-popover.component.html',
  styleUrls: ['./user-profile-popover.component.scss']
})
export class UserProfilePopoverComponent implements OnChanges {
  @Input() user: JUser | null = null;
  @Input() role = 'Участник платформы';
  @Input() team = 'Команда платформы';
  @Input() info = '';

  additionalInfo = '';
  avatarErrorMessage = '';
  isUpdatingAvatar = false;
  readonly acceptedAvatarTypes = 'image/png,image/jpeg,image/webp,image/gif';
  private readonly maxAvatarFileSize = 2 * 1024 * 1024;

  constructor(private _profilePreferences: UserProfilePreferencesService) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.user || changes.info) {
      this.syncAdditionalInfo();
    }
  }

  get avatarUrl(): string {
    return this.user?.avatarUrl || '';
  }

  get displayInitial(): string {
    return (this.user?.name || this.user?.email || '?').trim().charAt(0).toUpperCase() || '?';
  }

  removeAvatar(): void {
    if (!this.user?.id || this.isUpdatingAvatar) {
      return;
    }

    this.avatarErrorMessage = '';
    this.isUpdatingAvatar = true;
    this._profilePreferences
      .clearAvatar(this.user.id)
      .pipe(
        finalize(() => {
          this.isUpdatingAvatar = false;
        })
      )
      .subscribe({
        next: (avatarUrl) => {
          this.user = {
            ...this.user!,
            avatarUrl
          };
        },
        error: () => {
          this.avatarErrorMessage = 'Не удалось удалить аватар.';
        }
      });
  }

  saveAdditionalInfo(event: Event): void {
    if (!this.user?.id) {
      return;
    }

    const value = String((event.target as HTMLTextAreaElement)?.value ?? '');
    this.additionalInfo = value;
    this._profilePreferences.updateAdditionalInfo(this.user.id, value);
  }

  updateAvatar(event: Event): void {
    const input = event.target as HTMLInputElement | null;
    const file = input?.files?.[0];

    if (!input || !file || !this.user?.id || this.isUpdatingAvatar) {
      return;
    }

    if (!this.isSupportedAvatar(file)) {
      this.avatarErrorMessage = 'Поддерживаются PNG, JPG, WEBP и GIF.';
      input.value = '';
      return;
    }

    if (file.size > this.maxAvatarFileSize) {
      this.avatarErrorMessage = 'Размер файла должен быть не больше 2 МБ.';
      input.value = '';
      return;
    }

    const reader = new FileReader();

    reader.addEventListener('load', () => {
      const avatarUrl = typeof reader.result === 'string' ? reader.result : '';

      if (!avatarUrl) {
        this.avatarErrorMessage = 'Не удалось прочитать изображение.';
        return;
      }

      this.avatarErrorMessage = '';
      this.isUpdatingAvatar = true;
      this._profilePreferences
        .updateAvatar(this.user!.id, avatarUrl)
        .pipe(
          finalize(() => {
            this.isUpdatingAvatar = false;
          })
        )
        .subscribe({
          next: (nextAvatarUrl) => {
            this.user = {
              ...this.user!,
              avatarUrl: nextAvatarUrl
            };
          },
          error: () => {
            this.avatarErrorMessage = 'Не удалось сохранить аватар.';
          }
        });
    });

    reader.addEventListener('error', () => {
      this.avatarErrorMessage = 'Не удалось загрузить изображение.';
    });

    reader.readAsDataURL(file);
    input.value = '';
  }

  private isSupportedAvatar(file: File): boolean {
    return ['image/png', 'image/jpeg', 'image/webp', 'image/gif'].includes(file.type);
  }

  private syncAdditionalInfo(): void {
    if (!this.user?.id) {
      this.additionalInfo = this.info;
      return;
    }

    this.additionalInfo = this._profilePreferences.getAdditionalInfo(this.user.id, this.info);
  }
}
