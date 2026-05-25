import { Component, OnInit } from '@angular/core';
import { UntypedFormControl } from '@angular/forms';
import { UntilDestroy, untilDestroyed } from '@ngneat/until-destroy';
import { IssueType } from '@trungk18/interface/issue';
import { FilterQuery } from '@trungk18/project/state/filter/filter.query';
import { FilterService } from '@trungk18/project/state/filter/filter.service';
import { ProjectQuery } from '@trungk18/project/state/project/project.query';

@Component({
  selector: 'filter-toolbar',
  templateUrl: './board-filter.component.html',
  styleUrls: ['./board-filter.component.scss']
})
@UntilDestroy()
export class BoardFilterComponent implements OnInit {
  searchControl: UntypedFormControl = new UntypedFormControl('');
  statusControl: UntypedFormControl = new UntypedFormControl(null);
  assigneeControl: UntypedFormControl = new UntypedFormControl(null);
  criticalityControl: UntypedFormControl = new UntypedFormControl([]);
  issueTypeControl: UntypedFormControl = new UntypedFormControl(null);
  issueTypeOptions = [
    { value: IssueType.EPIC, label: 'EPIC', icon: 'story' },
    { value: IssueType.TASK, label: 'TASK', icon: 'task' }
  ];
  private isSyncingControls = false;

  constructor(
    public projectQuery: ProjectQuery,
    public filterService: FilterService,
    private _filterQuery: FilterQuery
  ) {}

  ngOnInit(): void {
    this._filterQuery.all$
      .pipe(untilDestroyed(this))
      .subscribe((filters) => {
        this.isSyncingControls = true;
        this.searchControl.setValue(filters.q, { emitEvent: false });
        this.statusControl.setValue(filters.statusId, { emitEvent: false });
        this.assigneeControl.setValue(filters.assigneeId, { emitEvent: false });
        this.criticalityControl.setValue(filters.criticalityIds, { emitEvent: false });
        this.issueTypeControl.setValue(filters.issueType, { emitEvent: false });
        this.isSyncingControls = false;
      });

    this.searchControl.valueChanges.pipe(untilDestroyed(this)).subscribe((query) => {
      if (this.isSyncingControls) {
        return;
      }
      this.filterService.updateSearchTerm(String(query ?? ''));
    });

    this.statusControl.valueChanges.pipe(untilDestroyed(this)).subscribe((statusId) => {
      if (this.isSyncingControls) {
        return;
      }
      this.filterService.updateStatusId(statusId || null);
    });

    this.assigneeControl.valueChanges.pipe(untilDestroyed(this)).subscribe((assigneeId) => {
      if (this.isSyncingControls) {
        return;
      }
      this.filterService.updateAssigneeId(assigneeId || null);
    });

    this.criticalityControl.valueChanges.pipe(untilDestroyed(this)).subscribe((criticalityIds) => {
      if (this.isSyncingControls) {
        return;
      }
      this.filterService.updateCriticalityIds(Array.isArray(criticalityIds) ? criticalityIds : []);
    });

    this.issueTypeControl.valueChanges.pipe(untilDestroyed(this)).subscribe((issueType) => {
      if (this.isSyncingControls) {
        return;
      }
      this.filterService.updateIssueType(issueType || null);
    });
  }

  resetFilters(): void {
    this.filterService.resetAll();
  }
}
