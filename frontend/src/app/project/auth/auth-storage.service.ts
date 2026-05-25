import { Injectable } from '@angular/core';

interface StoredSession {
  accessToken: string | null;
  refreshToken: string | null;
}

@Injectable({ providedIn: 'root' })
export class AuthStorageService {
  private readonly storageKey = 'jira-clone.auth.session';

  readSession(): StoredSession {
    if (typeof localStorage === 'undefined') {
      return { accessToken: null, refreshToken: null };
    }

    try {
      const rawValue = localStorage.getItem(this.storageKey);
      if (!rawValue) {
        return { accessToken: null, refreshToken: null };
      }

      const parsedValue = JSON.parse(rawValue) as Partial<StoredSession>;
      return {
        accessToken:
          typeof parsedValue.accessToken === 'string' ? parsedValue.accessToken : null,
        refreshToken:
          typeof parsedValue.refreshToken === 'string' ? parsedValue.refreshToken : null
      };
    } catch {
      this.clearSession();
      return { accessToken: null, refreshToken: null };
    }
  }

  writeSession(accessToken: string, refreshToken: string) {
    if (typeof localStorage === 'undefined') {
      return;
    }

    localStorage.setItem(
      this.storageKey,
      JSON.stringify({
        accessToken,
        refreshToken
      })
    );
  }

  clearSession() {
    if (typeof localStorage === 'undefined') {
      return;
    }

    localStorage.removeItem(this.storageKey);
  }
}
