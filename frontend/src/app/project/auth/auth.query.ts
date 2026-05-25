import { Injectable } from '@angular/core';
import { AuthStore, AuthState } from './auth.store';
import { Query } from '@datorama/akita';
import { map } from 'rxjs/operators';

@Injectable({ providedIn: 'root' })
export class AuthQuery extends Query<AuthState> {
  user$ = this.select('user');
  userId$ = this.user$.pipe(map((user) => user?.id ?? null));
  accessToken$ = this.select('accessToken');
  refreshToken$ = this.select('refreshToken');
  isInitialized$ = this.select('initialized');
  status$ = this.select('status');
  isInitializing$ = this.select((state) => state.status === 'initializing');
  isAuthenticated$ = this.select(
    (state) => state.status === 'authenticated' && !!state.user && !!state.accessToken
  );
  isUnauthorized$ = this.select((state) => state.status === 'unauthorized');

  constructor(protected store: AuthStore) {
    super(store);
  }
}
