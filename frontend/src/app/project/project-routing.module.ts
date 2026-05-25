import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { BoardComponent } from './pages/board/board.component';
import { SettingsComponent } from './pages/settings/settings.component';
import { ProjectComponent } from './project.component';
import { ProjectConst } from './config/const';
import { FullIssueDetailComponent } from './pages/full-issue-detail/full-issue-detail.component';
import { DocumentationComponent } from './pages/documentation/documentation.component';
import { OnboardingComponent } from './pages/onboarding/onboarding.component';
import { ProjectSettingsGuard } from './project-settings.guard';
import { ProjectReportsGuard } from './project-reports.guard';
import { ReportsComponent } from './pages/reports/reports.component';

const routes: Routes = [
  {
    path: '',
    component: ProjectComponent,
    children: [
      {
        path: 'board',
        component: BoardComponent
      },
      {
        path: 'settings',
        component: SettingsComponent,
        canActivate: [ProjectSettingsGuard]
      },
      {
        path: 'documentation',
        component: DocumentationComponent
      },
      {
        path: 'onboarding',
        component: OnboardingComponent
      },
      {
        path: 'dashboards',
        component: ReportsComponent,
        canActivate: [ProjectReportsGuard]
      },
      {
        path: 'reports',
        component: ReportsComponent,
        canActivate: [ProjectReportsGuard]
      },
      {
        path: `issue/:${ProjectConst.IssueId}`,
        component: FullIssueDetailComponent
      },
      {
        path: '',
        redirectTo: 'board',
        pathMatch: 'full'
      }
    ]
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class ProjectRoutingModule {}
