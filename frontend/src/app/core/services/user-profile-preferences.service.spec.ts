import { of } from 'rxjs';
import { UserProfilePreferencesService } from './user-profile-preferences.service';

describe('UserProfilePreferencesService', () => {
  let service: UserProfilePreferencesService;
  let authState: any;

  const authStore: any = {
    getValue: jasmine.createSpy('getValue').and.callFake(() => authState),
    update: jasmine.createSpy('update').and.callFake((updater: (state: any) => any) => {
      authState = updater(authState);
      return authState;
    })
  };
  const httpClient: any = {
    patch: jasmine.createSpy('patch')
  };

  beforeEach(() => {
    authState = {
      user: {
        id: 'user-1',
        name: 'Demo User',
        email: 'demo.user@example.com',
        avatarUrl: ''
      }
    };

    authStore.getValue.calls.reset();
    authStore.update.calls.reset();
    httpClient.patch.calls.reset();

    service = new UserProfilePreferencesService(authStore, httpClient);
  });

  it('keeps backend avatar when hydrating user', () => {
    const user = service.hydrateUser({
      id: 'user-1',
      name: 'Demo User',
      email: 'demo.user@example.com',
      avatarUrl: 'https://cdn.example.com/avatar.png'
    });

    expect(user.avatarUrl).toBe('https://cdn.example.com/avatar.png');
  });

  it('updates avatar through backend and patches current auth user', () => {
    httpClient.patch.and.returnValue(
      of({
        user: {
          id: 'user-1',
          avatar_url: 'data:image/png;base64,ZmFrZQ=='
        }
      })
    );

    let result = '';
    service.updateAvatar('user-1', 'data:image/png;base64,ZmFrZQ==').subscribe((value) => {
      result = value;
    });

    expect(httpClient.patch).toHaveBeenCalled();
    expect(httpClient.patch.calls.mostRecent().args[0]).toContain('/me/profile');
    expect(httpClient.patch.calls.mostRecent().args[1]).toEqual({
      avatar_url: 'data:image/png;base64,ZmFrZQ=='
    });
    expect(result).toBe('data:image/png;base64,ZmFrZQ==');
    expect(authState.user.avatarUrl).toBe('data:image/png;base64,ZmFrZQ==');
  });

  it('clears avatar through backend and patches current auth user', () => {
    authState.user.avatarUrl = 'data:image/png;base64,ZmFrZQ==';
    httpClient.patch.and.returnValue(
      of({
        user: {
          id: 'user-1',
          avatar_url: null
        }
      })
    );

    let result = 'non-empty';
    service.clearAvatar('user-1').subscribe((value) => {
      result = value;
    });

    expect(httpClient.patch.calls.mostRecent().args[1]).toEqual({
      avatar_url: null
    });
    expect(result).toBe('');
    expect(authState.user.avatarUrl).toBe('');
  });
});
