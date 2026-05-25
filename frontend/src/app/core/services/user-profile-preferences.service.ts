import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { JUser } from '@trungk18/interface/user';
import { AuthStore } from '@trungk18/project/auth/auth.store';
import { Observable, throwError } from 'rxjs';
import { map } from 'rxjs/operators';
import { environment } from 'src/environments/environment';

interface StoredUserProfilePreferences {
  additionalInfo?: string;
}

interface ProfileResponse {
  user: {
    id: string;
    avatar_url?: string | null;
  };
}

@Injectable({
  providedIn: 'root'
})
export class UserProfilePreferencesService {
  private readonly storageKey = 'platform-projects-user-profile-preferences';
  private readonly baseUrl = environment.apiUrl;
  private cache: Record<string, StoredUserProfilePreferences> | null = null;

  constructor(
    private _authStore: AuthStore,
    private _http: HttpClient
  ) {}

  hydrateUser(user: JUser): JUser {
    return {
      ...user,
      avatarUrl: user.avatarUrl || ''
    };
  }

  getAdditionalInfo(userId: string, fallback = ''): string {
    return this.getPreferences(userId).additionalInfo ?? fallback;
  }

  updateAdditionalInfo(userId: string, additionalInfo: string): void {
    this.updatePreferences(userId, { additionalInfo: additionalInfo.trim() });
  }

  updateAvatar(userId: string, avatarUrl: string): Observable<string> {
    return this.saveAvatar(userId, avatarUrl);
  }

  clearAvatar(userId: string): Observable<string> {
    return this.saveAvatar(userId, null);
  }

  private getPreferences(userId: string): StoredUserProfilePreferences {
    return this.readPreferences()[userId] ?? {};
  }

  private updatePreferences(
    userId: string,
    patch: StoredUserProfilePreferences
  ): void {
    const allPreferences = {
      ...this.readPreferences()
    };
    const currentPreferences = allPreferences[userId] ?? {};
    const nextPreferences = this.normalizePreferences({
      ...currentPreferences,
      ...patch
    });

    if (Object.keys(nextPreferences).length) {
      allPreferences[userId] = nextPreferences;
    } else {
      delete allPreferences[userId];
    }

    this.cache = allPreferences;
    this.persistPreferences();
  }

  private normalizePreferences(
    preferences: StoredUserProfilePreferences
  ): StoredUserProfilePreferences {
    const normalized: StoredUserProfilePreferences = {};

    if (preferences.additionalInfo?.trim()) {
      normalized.additionalInfo = preferences.additionalInfo.trim();
    }

    return normalized;
  }

  private saveAvatar(userId: string, avatarUrl: string | null): Observable<string> {
    const currentUserId = this._authStore.getValue().user?.id ?? null;

    if (currentUserId && currentUserId !== userId) {
      return throwError(() => new Error('Only current user avatar can be updated'));
    }

    return this._http
      .patch<ProfileResponse>(`${this.baseUrl}/me/profile`, {
        avatar_url: avatarUrl
      })
      .pipe(
        map(({ user }) => {
          const nextAvatarUrl = user.avatar_url ?? '';
          this.patchCurrentUser(user.id, { avatarUrl: nextAvatarUrl });
          return nextAvatarUrl;
        })
      );
  }

  private patchCurrentUser(userId: string, patch: Partial<JUser>): void {
    this._authStore.update((state) => {
      if (!state.user || state.user.id !== userId) {
        return state;
      }

      return {
        ...state,
        user: {
          ...state.user,
          ...patch
        }
      };
    });
  }

  private readPreferences(): Record<string, StoredUserProfilePreferences> {
    if (this.cache) {
      return this.cache;
    }

    if (typeof localStorage === 'undefined') {
      this.cache = {};
      return this.cache;
    }

    try {
      const rawValue = localStorage.getItem(this.storageKey);
      this.cache = rawValue ? JSON.parse(rawValue) : {};
    } catch {
      this.cache = {};
    }

    return this.cache;
  }

  private persistPreferences(): void {
    if (typeof localStorage === 'undefined') {
      return;
    }

    localStorage.setItem(this.storageKey, JSON.stringify(this.cache ?? {}));
  }
}
