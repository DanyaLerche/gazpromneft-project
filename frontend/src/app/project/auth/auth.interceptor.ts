import {
  HttpErrorResponse,
  HttpEvent,
  HttpHandler,
  HttpInterceptor,
  HttpRequest
} from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError, switchMap } from 'rxjs/operators';
import { environment } from 'src/environments/environment';
import { AuthQuery } from './auth.query';
import { AuthService } from './auth.service';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  constructor(private _authQuery: AuthQuery, private _authService: AuthService) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    if (!this.isApiRequest(req.url) || this.isPublicAuthRequest(req.url)) {
      return next.handle(req);
    }

    const requestWithToken = this.withAccessToken(req, this._authQuery.getValue().accessToken);

    return next.handle(requestWithToken).pipe(
      catchError((error: HttpErrorResponse) => {
        if (!this.shouldRefresh(error, req.url)) {
          return throwError(error);
        }

        return this._authService.refreshTokens().pipe(
          switchMap((response) =>
            next.handle(this.withAccessToken(req, response.access_token))
          ),
          catchError((refreshError) => {
            this._authService.handleSessionExpired();
            return throwError(refreshError);
          })
        );
      })
    );
  }

  private isApiRequest(url: string): boolean {
    return url.startsWith(environment.apiUrl);
  }

  private isPublicAuthRequest(url: string): boolean {
    return (
      url.includes('/auth/login') ||
      url.includes('/auth/register') ||
      url.includes('/auth/refresh')
    );
  }

  private shouldRefresh(error: HttpErrorResponse, url: string): boolean {
    return (
      error.status === 401 &&
      !url.includes('/auth/refresh') &&
      !!this._authQuery.getValue().refreshToken
    );
  }

  private withAccessToken(
    req: HttpRequest<any>,
    accessToken: string | null
  ): HttpRequest<any> {
    if (!accessToken) {
      return req;
    }

    return req.clone({
      setHeaders: {
        Authorization: `Bearer ${accessToken}`
      }
    });
  }
}
