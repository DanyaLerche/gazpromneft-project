import { Injectable } from '@angular/core';
import { FilterState, FilterStore, createInitialFilterState } from './filter.store';

@Injectable({
  providedIn: 'root'
})
export class FilterService {
  constructor(private store: FilterStore) {}

  updateSearchTerm(q: string) {
    this.store.update({
      q
    });
  }

  updateStatusId(statusId: string | null) {
    this.store.update({
      statusId
    });
  }

  updateAssigneeId(assigneeId: string | null) {
    this.store.update({
      assigneeId
    });
  }

  updateCriticalityIds(criticalityIds: string[]) {
    this.store.update({
      criticalityIds
    });
  }

  updateIssueType(issueType: string | null) {
    this.store.update((state) => ({
      ...state,
      issueType
    }));
  }

  resetAll() {
    this.store.update((state) => ({
      ...state,
      ...createInitialFilterState()
    }));
  }

  patch(value: Partial<FilterState>) {
    this.store.update((state) => {
      return {
        ...state,
        ...value
      };
    });
  }
}
