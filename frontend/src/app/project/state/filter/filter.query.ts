import { Injectable } from '@angular/core';
import { Query } from '@datorama/akita';
import { FilterStore, FilterState } from './filter.store';

@Injectable({ providedIn: 'root' })
export class FilterQuery extends Query<FilterState> {
  any$ = this.select(
    ({
      q,
      statusId,
      assigneeId,
      criticalityIds,
      issueType
    }) =>
      !!q ||
      !!statusId ||
      !!assigneeId ||
      criticalityIds.length > 0 ||
      !!issueType
  );
  all$ = this.select();
  q$ = this.select('q');
  statusId$ = this.select('statusId');
  assigneeId$ = this.select('assigneeId');
  criticalityIds$ = this.select('criticalityIds');
  issueType$ = this.select('issueType');

  constructor(protected store: FilterStore) {
    super(store);
  }
}
