import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { AuthRoutingModule } from './auth-routing.module';
import { AuthShellComponent } from './auth-shell/auth-shell.component';
import { LoginPageComponent } from './login-page/login-page.component';
import { RegisterPageComponent } from './register-page/register-page.component';
import { VerifyEmailPageComponent } from './verify-email-page/verify-email-page.component';
import { AppUiModule } from '../shared/ui';

@NgModule({
  declarations: [AuthShellComponent, LoginPageComponent, RegisterPageComponent, VerifyEmailPageComponent],
  imports: [CommonModule, ReactiveFormsModule, RouterModule, AuthRoutingModule, AppUiModule]
})
export class AuthModule {}
