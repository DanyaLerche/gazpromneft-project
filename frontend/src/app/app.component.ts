import {
  Component,
  ViewEncapsulation,
  AfterViewInit,
  ChangeDetectorRef,
  OnInit
} from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';
import { environment } from '../environments/environment';
import { ProjectQuery } from './project/state/project/project.query';
import { GoogleAnalyticsService } from './core/services/google-analytics.service';
import { AuthQuery } from './project/auth/auth.query';
import { AuthService } from './project/auth/auth.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
  encapsulation: ViewEncapsulation.None
})
export class AppComponent implements AfterViewInit, OnInit {
  constructor(
    public router: Router,
    public projectQuery: ProjectQuery,
    public authQuery: AuthQuery,
    private _cdr: ChangeDetectorRef,
    private _googleAnalytics: GoogleAnalyticsService,
    private _authService: AuthService
  ) {
    if (environment.production) {
      this.router.events.subscribe(this.handleGoogleAnalytics);
    }
  }

  handleGoogleAnalytics = (event: any): void => {
    if (event instanceof NavigationEnd) {
      this._googleAnalytics.sendPageView(event.urlAfterRedirects);
    }
  };

  ngOnInit() {
    this._authService.initialize().subscribe();
  }

  ngAfterViewInit() {
    this._cdr.detectChanges();
  }
}
