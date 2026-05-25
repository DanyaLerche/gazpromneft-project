import { Component, OnInit } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { getApiErrorMessage } from '@trungk18/core/utils/api-error';
import { NoWhitespaceValidator } from '@trungk18/core/validators/no-whitespace.validator';
import { AuthService } from '@trungk18/project/auth/auth.service';
import { LoginPayload } from '@trungk18/project/auth/loginPayload';
import { finalize } from 'rxjs/operators';

@Component({
  selector: 'app-login-page',
  templateUrl: './login-page.component.html',
  styleUrls: ['./login-page.component.scss']
})
export class LoginPageComponent implements OnInit {
  isSubmitting = false;
  serverError = '';
  infoMessage = '';
  private returnUrl = '/projects';

  form = this._fb.group({
    email: ['', [Validators.required, Validators.email, NoWhitespaceValidator()]],
    password: ['', [Validators.required]]
  });

  constructor(
    private _fb: FormBuilder,
    private _authService: AuthService,
    private _router: Router,
    private _route: ActivatedRoute
  ) {}

  ngOnInit(): void {
    const email = this._route.snapshot.queryParamMap.get('email');
    const reason = this._route.snapshot.queryParamMap.get('reason');
    this.returnUrl = this.normalizeReturnUrl(this._route.snapshot.queryParamMap.get('returnUrl'));

    if (email) {
      this.form.patchValue({ email });
    }

    if (reason === 'session-expired') {
      this.infoMessage = 'Сессия истекла. Войдите снова, чтобы продолжить работу.';
    } else if (reason === 'email-verified') {
      this.infoMessage = 'Email подтвержден. Теперь можно войти в систему.';
    }
  }

  submit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.isSubmitting = true;
    this.serverError = '';

    this._authService
      .login(this.form.getRawValue() as LoginPayload)
      .pipe(
        finalize(() => {
          this.isSubmitting = false;
        })
      )
      .subscribe({
        next: () => {
          this._router.navigateByUrl(this.returnUrl);
        },
        error: (error) => {
          this.serverError = this.formatError(error);
        }
      });
  }

  private formatError(error: any): string {
    if (error?.status === 400) {
      return 'Неверный email или пароль.';
    }

    if (error?.status === 403) {
      if (String(error?.error?.detail || '').toLowerCase().includes('email is not verified')) {
        return 'Сначала подтвердите email кодом из письма.';
      }
      return 'Пользователь деактивирован. Обратитесь к администратору.';
    }

    return getApiErrorMessage(error, 'Не удалось выполнить вход. Попробуйте ещё раз.');
  }

  private normalizeReturnUrl(value: string | null): string {
    if (!value || !value.startsWith('/')) {
      return '/projects';
    }

    return value;
  }
}
