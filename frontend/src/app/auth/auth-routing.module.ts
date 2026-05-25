import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { GuestGuard } from '@trungk18/project/auth/guest.guard';
import { AuthShellComponent } from './auth-shell/auth-shell.component';
import { LoginPageComponent } from './login-page/login-page.component';
import { RegisterPageComponent } from './register-page/register-page.component';
import { VerifyEmailPageComponent } from './verify-email-page/verify-email-page.component';

const routes: Routes = [
  {
    path: '',
    component: AuthShellComponent,
    children: [
      {
        path: 'login',
        component: LoginPageComponent,
        canActivate: [GuestGuard]
      },
      {
        path: 'register',
        component: RegisterPageComponent,
        canActivate: [GuestGuard]
      },
      {
        path: 'verify-email',
        component: VerifyEmailPageComponent,
        canActivate: [GuestGuard]
      },
      {
        path: '',
        redirectTo: 'login',
        pathMatch: 'full'
      }
    ]
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class AuthRoutingModule {}
