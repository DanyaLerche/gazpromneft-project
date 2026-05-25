import { AuthService } from './auth.service';
import { of } from 'rxjs';

describe('AuthService', () => {
  let service: AuthService;

  const httpBackend: any = {
    handle: jasmine.createSpy('handle').and.returnValue(of({}))
  };
  const authStore: any = {
    setLoading: jasmine.createSpy('setLoading').and.callThrough(),
    update: jasmine.createSpy('update').and.callThrough(),
    setError: jasmine.createSpy('setError').and.callThrough()
  };
  const authQuery: any = {
    getValue: jasmine.createSpy('getValue').and.returnValue({
      user: null,
      accessToken: null,
      refreshToken: null,
      initialized: false,
      status: 'unauthorized'
    })
  };
  const storage: any = {
    readSession: jasmine.createSpy('readSession').and.returnValue({
      accessToken: null,
      refreshToken: null
    }),
    writeSession: jasmine.createSpy('writeSession').and.callThrough(),
    clearSession: jasmine.createSpy('clearSession').and.callThrough()
  };
  const router: any = {
    navigateByUrl: jasmine.createSpy('navigateByUrl').and.callThrough(),
    navigate: jasmine.createSpy('navigate').and.callThrough(),
    url: '/projects'
  };
  const profilePreferences: any = {
    hydrateUser: jasmine.createSpy('hydrateUser').and.callFake((user: any) => user)
  };

  beforeEach(() => {
    authQuery.getValue.calls.reset();
    authQuery.getValue.and.returnValue({
      user: null,
      accessToken: null,
      refreshToken: null,
      initialized: false,
      status: 'unauthorized'
    });

    service = new AuthService(
      httpBackend,
      authStore,
      authQuery,
      storage,
      router,
      profilePreferences
    );
  });

  it('returns false from initialize when no saved session exists', () => {
    let result = true;

    service.initialize().subscribe((value) => {
      result = value;
    });

    expect(storage.readSession).toHaveBeenCalled();
    expect(storage.clearSession).toHaveBeenCalled();
    expect(authStore.setError).toHaveBeenCalledWith(null);
    expect(authStore.update).toHaveBeenCalled();
    expect(result).toBeFalse();
  });

  it('recognizes authenticated state', () => {
    authQuery.getValue.and.returnValue({
      user: { id: 'user-1' },
      accessToken: 'token',
      refreshToken: 'refresh',
      initialized: true,
      status: 'authenticated'
    });

    expect(service.isAuthenticated()).toBeTrue();
  });

  it('logs out locally when access token is missing', () => {
    authQuery.getValue.and.returnValue({
      user: null,
      accessToken: null,
      refreshToken: null,
      initialized: true,
      status: 'unauthorized'
    });

    service.logout('/auth/login').subscribe();

    expect(storage.clearSession).toHaveBeenCalled();
    expect(router.navigateByUrl).toHaveBeenCalledWith('/auth/login');
  });
});
