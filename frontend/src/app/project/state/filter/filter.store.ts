import { Injectable } from '@angular/core';
import { Store, StoreConfig } from '@datorama/akita';

export interface FilterState {
  q: string;
  statusId: string | null;
  assigneeId: string | null;
  criticalityIds: string[];
  issueType: string | null;
}

export function createInitialFilterState(): FilterState {
  return {
    q: '',
    statusId: null,
    assigneeId: null,
    criticalityIds: [],
    issueType: null
  };
}

@Injectable({
  providedIn: 'root'
})
@StoreConfig({
  name: 'filter'
})
export class FilterStore extends Store<FilterState> {
  constructor() {
    super(createInitialFilterState());
  }
}
