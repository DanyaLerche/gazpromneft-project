import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';
import { JiraControlModule } from '@trungk18/jira-control/jira-control.module';
import { NzPopoverModule } from 'ng-zorro-antd/popover';
import { ScheduleRoutingModule } from './schedule-routing.module';
import { SchedulePageComponent } from './schedule-page/schedule-page.component';
import { AppUiModule } from '../shared/ui';

@NgModule({
  declarations: [SchedulePageComponent],
  imports: [
    CommonModule,
    ReactiveFormsModule,
    ScheduleRoutingModule,
    JiraControlModule,
    NzPopoverModule,
    AppUiModule
  ]
})
export class ScheduleModule {}
