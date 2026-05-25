import { HttpBackend, HttpClient, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { AppRole } from '@trungk18/interface/role';
import { JUser } from '@trungk18/interface/user';
import { Observable, of, throwError } from 'rxjs';
import {
  catchError,
  finalize,
  map,
  shareReplay,
  switchMap,
  tap
} from 'rxjs/operators';
import { UserProfilePreferencesService } from '@trungk18/core/services/user-profile-preferences.service';
import { environment } from 'src/environments/environment';
import { AuthQuery } from './auth.query';
import { AuthStorageService } from './auth-storage.service';
import { createInitialAuthState, AuthStore } from './auth.store';
import { LoginPayload } from './loginPayload';
import { RegisterPayload } from './registerPayload';

interface ApiUser {
  id: string;
  email: string;
  full_name: string;
  avatar_url?: string | null;
  is_active: boolean;
  app_role: AppRole;
  created_at: string;
}

interface RegisterResponse {
  email: string;
  verification_required: boolean;
}

export interface RegisterResult {
  email: string;
  verificationRequired: boolean;
}

interface VerifyEmailResponse {
  verified: boolean;
}

interface ResendVerificationResponse {
  sent: boolean;
}

interface LoginResponse {
  access_token: string;
  refresh_token: string;
  user: ApiUser;
}

interface MeResponse {
  user: ApiUser;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly baseUrl = environment.apiUrl;
  private readonly rawHttp: HttpClient;
  private initRequest$: Observable<boolean> | null = null;
  private refreshRequest$: Observable<LoginResponse> | null = null;

  constructor(
    httpBackend: HttpBackend,
    private _store: AuthStore,
    private _query: AuthQuery,
    private _storage: AuthStorageService,
    private _router: Router,
    private _profilePreferences: UserProfilePreferencesService
  ) {
    this.rawHttp = new HttpClient(httpBackend);
  }

  initialize(): Observable<boolean> {
    const state = this._query.getValue();

    if (state.initialized) {
      return of(this.isAuthenticated());
    }

    if (this.initRequest$) {
      return this.initRequest$;
    }

    const session = this._storage.readSession();

    if (!session.accessToken && !session.refreshToken) {
      this.clearSession();
      return of(false);
    }

    this._store.update((currentState) => ({
      ...currentState,
      accessToken: session.accessToken,
      refreshToken: session.refreshToken,
      status: 'initializing'
    }));

    const init$ = (
      session.accessToken
        ? this.fetchMe()
        : this.refreshTokens().pipe(switchMap(() => this.fetchMe(false)))
    ).pipe(
      map(() => true),
      catchError(() => {
        this.clearSession();
        return of(false);
      }),
      finalize(() => {
        this.initRequest$ = null;
      }),
      shareReplay(1)
    );

    this.initRequest$ = init$;
    return init$;
  }

  login(payload: LoginPayload): Observable<JUser> {
    this._store.setLoading(true);
    this._store.setError(null);

    return this.rawHttp
      .post<LoginResponse>(`${this.baseUrl}/auth/login`, {
        email: payload.email.trim().toLowerCase(),
        password: payload.password
      })
      .pipe(
        tap((response) => {
          this.applyAuthResponse(response);
        }),
        map(({ user }) => this.mapUser(user)),
        finalize(() => {
          this._store.setLoading(false);
        }),
        catchError((error) => {
          this._store.setError(error);
          return throwError(error);
        })
      );
  }

  register(payload: RegisterPayload): Observable<RegisterResult> {
    this._store.setError(null);
    return this.rawHttp
      .post<RegisterResponse>(`${this.baseUrl}/auth/register`, {
        email: payload.email.trim().toLowerCase(),
        full_name: payload.fullName.trim(),
        password: payload.password
      })
      .pipe(
        map((response) => ({
          email: response.email,
          verificationRequired: response.verification_required
        })),
        catchError((error) => {
          this._store.setError(error);
          return throwError(error);
        })
      );
  }

  verifyEmail(email: string, code: string): Observable<boolean> {
    this._store.setError(null);
    return this.rawHttp
      .post<VerifyEmailResponse>(`${this.baseUrl}/auth/verify-email`, {
        email: email.trim().toLowerCase(),
        code: code.trim()
      })
      .pipe(
        map((response) => response.verified),
        catchError((error) => {
          this._store.setError(error);
          return throwError(error);
        })
      );
  }

  resendVerification(email: string): Observable<boolean> {
    this._store.setError(null);
    return this.rawHttp
      .post<ResendVerificationResponse>(`${this.baseUrl}/auth/resend-verification`, {
        email: email.trim().toLowerCase()
      })
      .pipe(
        map((response) => response.sent),
        catchError((error) => {
          this._store.setError(error);
          return throwError(error);
        })
      );
  }

  refreshTokens(): Observable<LoginResponse> {
    const refreshToken = this._query.getValue().refreshToken;

    if (!refreshToken) {
      return throwError(new Error('Refresh token is missing'));
    }

    if (this.refreshRequest$) {
      return this.refreshRequest$;
    }

    const refresh$ = this.rawHttp
      .post<LoginResponse>(`${this.baseUrl}/auth/refresh`, {
        refresh_token: refreshToken
      })
      .pipe(
        tap((response) => {
          this.applyAuthResponse(response);
        }),
        finalize(() => {
          this.refreshRequest$ = null;
        }),
        shareReplay(1)
      );

    this.refreshRequest$ = refresh$;
    return refresh$;
  }

  fetchMe(allowRefresh = true): Observable<JUser> {
    const accessToken = this._query.getValue().accessToken;

    if (!accessToken) {
      return throwError(new Error('Access token is missing'));
    }

    return this.rawHttp
      .get<MeResponse>(`${this.baseUrl}/me`, {
        headers: this.createAuthHeaders(accessToken)
      })
      .pipe(
        map(({ user }) => this.mapUser(user)),
        tap((user) => {
          this._store.update((state) => ({
            ...state,
            user,
            initialized: true,
            status: 'authenticated'
          }));
        }),
        catchError((error: HttpErrorResponse) => {
          if (allowRefresh && error.status === 401 && this._query.getValue().refreshToken) {
            return this.refreshTokens().pipe(switchMap(() => this.fetchMe(false)));
          }

          return throwError(error);
        })
      );
  }

  logout(redirectUrl = '/auth/login'): Observable<void> {
    const accessToken = this._query.getValue().accessToken;

    if (!accessToken) {
      this.clearSession();
      this._router.navigateByUrl(redirectUrl);
      return of(void 0);
    }

    return this.rawHttp
      .post<void>(
        `${this.baseUrl}/auth/logout`,
        {},
        { headers: this.createAuthHeaders(accessToken) }
      )
      .pipe(
        catchError((error: HttpErrorResponse) => {
          if (error.status === 401 && this._query.getValue().refreshToken) {
            return this.refreshTokens().pipe(
              switchMap(() =>
                this.rawHttp.post<void>(
                  `${this.baseUrl}/auth/logout`,
                  {},
                  {
                    headers: this.createAuthHeaders(this._query.getValue().accessToken)
                  }
                )
              ),
              catchError(() => of(void 0))
            );
          }

          return of(void 0);
        }),
        tap(() => {
          this.clearSession();
          this._router.navigateByUrl(redirectUrl);
        })
      );
  }

  handleSessionExpired() {
    const returnUrl = this.getSafeReturnUrl();
    this.clearSession();
    this._router.navigate(['/auth/login'], {
      queryParams: {
        reason: 'session-expired',
        returnUrl
      }
    });
  }

  isAuthenticated(): boolean {
    const state = this._query.getValue();
    return state.status === 'authenticated' && !!state.user && !!state.accessToken;
  }

  setUser(user: JUser) {
    this._store.update((state) => ({
      ...state,
      user
    }));
  }

  private applyAuthResponse(response: LoginResponse) {
    const user = this.mapUser(response.user);
    this._storage.writeSession(response.access_token, response.refresh_token);
    this._store.update((state) => ({
      ...state,
      user,
      accessToken: response.access_token,
      refreshToken: response.refresh_token,
      initialized: true,
      status: 'authenticated'
    }));
  }

  private clearSession() {
    this._storage.clearSession();
    this._store.setError(null);
    this._store.update(() => ({
      ...createInitialAuthState(),
      initialized: true,
      status: 'unauthorized'
    }));
  }

  private createAuthHeaders(accessToken: string | null): HttpHeaders {
    return new HttpHeaders({
      Authorization: `Bearer ${accessToken ?? ''}`
    });
  }

  private getSafeReturnUrl(): string {
    const currentUrl = this._router.url || '/projects';
    return currentUrl.startsWith('/auth') ? '/projects' : currentUrl;
  }

  private mapUser(user: ApiUser): JUser {
    return this._profilePreferences.hydrateUser({
      id: user.id,
      name: user.full_name,
      email: user.email,
      avatarUrl: user.avatar_url ?? '',
      isActive: user.is_active,
      appRole: user.app_role,
      createdAt: user.created_at,
      updatedAt: user.created_at,
      issueIds: []
    });
  }
}
