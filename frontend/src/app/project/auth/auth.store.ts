import { Injectable } from '@angular/core';
import { JUser } from '@trungk18/interface/user';
import { Store, StoreConfig } from '@datorama/akita';

export type AuthStatus = 'initializing' | 'authenticated' | 'unauthorized';

export interface AuthState {
  user: JUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  initialized: boolean;
  status: AuthStatus;
}

export function createInitialAuthState(): AuthState {
  return {
    user: null,
    accessToken: null,
    refreshToken: null,
    initialized: false,
    status: 'initializing'
  };
}

@Injectable({ providedIn: 'root' })
@StoreConfig({
  name: 'auth'
})
export class AuthStore extends Store<AuthState> {
  constructor() {
    super(createInitialAuthState());
  }
}
