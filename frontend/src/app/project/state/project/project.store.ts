import { JProject } from '@trungk18/interface/project';
import { Store, StoreConfig } from '@datorama/akita';
import { Injectable } from '@angular/core';
import { ProjectCategory } from '@trungk18/interface/project';

export type ProjectState = JProject;

export function createInitialState(): ProjectState {
  return {
    id: '',
    key: '',
    name: '',
    createdBy: '',
    createdAt: '',
    description: '',
    category: ProjectCategory.SOFTWARE,
    updateAt: '',
    currentUserRole: null,
    newEmployeeMode: false,
    onboardingAssigneeIds: [],
    issues: [],
    users: [],
    statuses: [],
    criticalities: []
  };
}

@Injectable({
  providedIn: 'root'
})
@StoreConfig({
  name: 'project'
})
export class ProjectStore extends Store<ProjectState> {
  constructor() {
    super(createInitialState());
  }
}
