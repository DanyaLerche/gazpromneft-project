import { Component, OnInit } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { getApiErrorMessage } from '@trungk18/core/utils/api-error';
import { NoWhitespaceValidator } from '@trungk18/core/validators/no-whitespace.validator';
import { AuthService } from '@trungk18/project/auth/auth.service';
import { finalize } from 'rxjs/operators';

@Component({
  selector: 'app-verify-email-page',
  templateUrl: './verify-email-page.component.html',
  styleUrls: ['./verify-email-page.component.scss']
})
export class VerifyEmailPageComponent implements OnInit {
  isSubmitting = false;
  isResending = false;
  serverError = '';
  infoMessage = '';
  email = '';

  form = this._fb.group({
    code: ['', [Validators.required, Validators.minLength(4), Validators.maxLength(12), NoWhitespaceValidator()]]
  });

  constructor(
    private _fb: FormBuilder,
    private _authService: AuthService,
    private _route: ActivatedRoute,
    private _router: Router
  ) {}

  ngOnInit(): void {
    this.email = (this._route.snapshot.queryParamMap.get('email') || '').trim().toLowerCase();
    if (!this.email) {
      this._router.navigate(['/auth/register']);
    }
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.isSubmitting = true;
    this.serverError = '';
    this.infoMessage = '';

    this._authService
      .verifyEmail(this.email, this.form.getRawValue().code ?? '')
      .pipe(finalize(() => (this.isSubmitting = false)))
      .subscribe({
        next: () => {
          this._router.navigate(['/auth/login'], {
            queryParams: { email: this.email, reason: 'email-verified' }
          });
        },
        error: (error) => {
          this.serverError = this.formatVerifyError(error);
        }
      });
  }

  resend(): void {
    if (!this.email) {
      return;
    }

    this.isResending = true;
    this.serverError = '';
    this.infoMessage = '';

    this._authService
      .resendVerification(this.email)
      .pipe(finalize(() => (this.isResending = false)))
      .subscribe({
        next: () => {
          this.infoMessage = 'Код подтверждения отправлен повторно.';
        },
        error: (error) => {
          this.serverError = this.formatResendError(error);
        }
      });
  }

  private formatVerifyError(error: any): string {
    if (error?.status === 400) {
      return 'Неверный или просроченный код подтверждения.';
    }

    return getApiErrorMessage(error, 'Не удалось подтвердить email. Попробуйте ещё раз.');
  }

  private formatResendError(error: any): string {
    if (error?.status === 429) {
      return 'Повторная отправка временно ограничена. Подождите немного.';
    }

    return getApiErrorMessage(error, 'Не удалось отправить код повторно. Попробуйте позже.');
  }
}
