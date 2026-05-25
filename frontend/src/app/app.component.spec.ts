import { AppComponent } from '@trungk18/app.component';
import { NavigationEnd } from '@angular/router';
import { of } from 'rxjs';
import { environment } from '../environments/environment';

describe('AppComponent', () => {
  let component: AppComponent;

  const router: any = {
    events: {
      subscribe: jasmine.createSpy('subscribe')
    }
  };
  const projectQuery: any = {};
  const authQuery: any = {};
  const changeDetectorRef: any = {
    detectChanges: jasmine.createSpy('detectChanges')
  };
  const googleAnalyticsService: any = {
    sendPageView: jasmine.createSpy('sendPageView').and.callThrough()
  };
  const authService: any = {
    initialize: jasmine.createSpy('initialize').and.returnValue(of(true))
  };

  beforeEach(() => {
    environment.production = true;
    component = new AppComponent(
      router,
      projectQuery,
      authQuery,
      changeDetectorRef,
      googleAnalyticsService,
      authService
    );
  });

  it('should subscribe to router events in production', () => {
    expect(router.events.subscribe).toHaveBeenCalled();
  });

  it('should initialize auth on init', () => {
    component.ngOnInit();
    expect(authService.initialize).toHaveBeenCalled();
  });

  it('should be able to make ng After View Init', () => {
    component.ngAfterViewInit();
    expect(changeDetectorRef.detectChanges).toHaveBeenCalled();
  });

  it('should be able to handle Google Analytics', () => {
    component.handleGoogleAnalytics(new NavigationEnd(1, '/', '/'));

    expect(googleAnalyticsService.sendPageView).toHaveBeenCalled();
  });

  it('should not be able to handle Google Analytics', () => {
    googleAnalyticsService.sendPageView.calls.reset();
    component.handleGoogleAnalytics({});

    expect(googleAnalyticsService.sendPageView).not.toHaveBeenCalled();
  });
});
