import { Component } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { getApiErrorMessage } from '@trungk18/core/utils/api-error';
import { NoWhitespaceValidator } from '@trungk18/core/validators/no-whitespace.validator';
import { AuthService } from '@trungk18/project/auth/auth.service';
import { RegisterPayload } from '@trungk18/project/auth/registerPayload';
import { finalize } from 'rxjs/operators';

@Component({
  selector: 'app-register-page',
  templateUrl: './register-page.component.html',
  styleUrls: ['./register-page.component.scss']
})
export class RegisterPageComponent {
  isSubmitting = false;
  serverError = '';

  form = this._fb.group({
    email: ['', [Validators.required, Validators.email, NoWhitespaceValidator()]],
    fullName: [
      '',
      [Validators.required, Validators.maxLength(200), NoWhitespaceValidator()]
    ],
    password: ['', [Validators.required, Validators.minLength(8)]]
  });

  constructor(
    private _fb: FormBuilder,
    private _authService: AuthService,
    private _router: Router
  ) {}

  submit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.isSubmitting = true;
    this.serverError = '';

    this._authService
      .register(this.form.getRawValue() as RegisterPayload)
      .pipe(
        finalize(() => {
          this.isSubmitting = false;
        })
      )
      .subscribe({
        next: (result) => {
          this._router.navigate(['/auth/verify-email'], {
            queryParams: { email: result.email }
          });
        },
        error: (error) => {
          this.serverError = this.formatError(error);
        }
      });
  }

  private formatError(error: any): string {
    if (error?.status === 409) {
      return 'Этот email уже зарегистрирован.';
    }

    return getApiErrorMessage(
      error,
      'Не удалось завершить регистрацию. Проверьте данные и повторите попытку.'
    );
  }
}
