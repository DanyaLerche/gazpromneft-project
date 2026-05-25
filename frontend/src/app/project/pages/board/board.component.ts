import { Component, OnInit } from '@angular/core';
import { UntilDestroy, untilDestroyed } from '@ngneat/until-destroy';
import { FilterState, createInitialFilterState } from '@trungk18/project/state/filter/filter.store';
import { FilterQuery } from '@trungk18/project/state/filter/filter.query';
import { FilterService } from '@trungk18/project/state/filter/filter.service';
import { ProjectQuery } from '@trungk18/project/state/project/project.query';
import { ProjectService } from '@trungk18/project/state/project/project.service';
import { combineLatest } from 'rxjs';
import { debounceTime, distinctUntilChanged, map } from 'rxjs/operators';
import { ActivatedRoute, Params, Router } from '@angular/router';

@Component({
  selector: 'board',
  templateUrl: './board.component.html',
  styleUrls: ['./board.component.scss']
})
@UntilDestroy()
export class BoardComponent implements OnInit {
  breadcrumbs: string[] = ['Проекты', 'Канбан-доска'];
  showNoStatuses$ = combineLatest([this.projectQuery.statuses$, this.projectQuery.isLoading$]).pipe(
    map(([statuses, isLoading]) => !isLoading && statuses.length === 0)
  );
  showNoResults$ = combineLatest([
    this.projectQuery.statuses$,
    this.projectQuery.issues$,
    this._filterQuery.any$
  ]).pipe(
    map(
      ([statuses, issues, hasFilters]) =>
        statuses.length > 0 && hasFilters && issues.length === 0
    )
  );

  constructor(
    public projectQuery: ProjectQuery,
    private _filterQuery: FilterQuery,
    private _projectService: ProjectService,
    private _filterService: FilterService,
    private _route: ActivatedRoute,
    private _router: Router
  ) {}

  ngOnInit(): void {
    this._route.queryParamMap
      .pipe(
        map((params) => this.normalizeFilters({
          q: params.get('q') ?? '',
          statusId: params.get('statusId'),
          assigneeId: params.get('assigneeId'),
          criticalityIds: (params.get('criticalityIds') ?? '')
            .split(',')
            .map((value) => value.trim())
            .filter(Boolean),
          issueType: params.get('issueType')
        })),
        distinctUntilChanged((previous, current) => this.serializeFilters(previous) === this.serializeFilters(current)),
        untilDestroyed(this)
      )
      .subscribe((filters) => {
        this._filterService.patch(filters);
      });

    this._filterQuery.all$
      .pipe(
        debounceTime(150),
        distinctUntilChanged((previous, current) => this.serializeFilters(previous) === this.serializeFilters(current)),
        untilDestroyed(this)
      )
      .subscribe((filters) => {
        this._projectService.loadIssues(filters);
        this._router.navigate([], {
          relativeTo: this._route,
          queryParams: this.buildQueryParams(filters),
          replaceUrl: true
        });
      });
  }

  private normalizeFilters(filters: Partial<FilterState>): FilterState {
    return {
      ...createInitialFilterState(),
      ...filters,
      criticalityIds: [...(filters.criticalityIds ?? [])]
    };
  }

  private buildQueryParams(filters: FilterState): Params {
    return {
      q: filters.q || null,
      statusId: filters.statusId || null,
      assigneeId: filters.assigneeId || null,
      criticalityIds: filters.criticalityIds.length ? filters.criticalityIds.join(',') : null,
      issueType: filters.issueType || null
    };
  }

  private serializeFilters(filters: FilterState): string {
    return JSON.stringify({
      ...filters,
      criticalityIds: [...filters.criticalityIds].sort()
    });
  }
}
