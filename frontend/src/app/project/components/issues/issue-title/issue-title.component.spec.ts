import { UntypedFormControl } from '@angular/forms';
import { IssueTitleComponent } from './issue-title.component';
import {SimpleChange} from '@angular/core';
import {IssuePriority, IssueStatus, IssueType} from '@trungk18/interface/issue';

describe('IssueTitleComponent', () => {
  let component: IssueTitleComponent;

  const projectService: any = {
    updateIssue: jasmine.createSpy('updateIssue').and.callThrough()
  };

  beforeEach(() => {
    component = new IssueTitleComponent(
      projectService
    );
    component.issue = {
      id: 'issue-1',
      key: 'DEMO-1',
      title: 'Current title',
      type: IssueType.BUG,
      status: IssueStatus.ЗАДЕРЖКА,
      statusId: 'status-1',
      priority: IssuePriority.HIGH,
      listPosition: 0,
      description: '',
      estimate: 0,
      timeSpent: 0,
      timeRemaining: 0,
      createdAt: '',
      updatedAt: '',
      reporterId: '',
      authorId: '',
      userIds: [],
      comments: [],
      projectId: ''
    };
    component.titleControl = new UntypedFormControl('test');
  });

  it('should be able to make onBlur action', () => {
    component.titleControl.setValue('Updated title');
    component.onBlur();
    expect(projectService.updateIssue).toHaveBeenCalledWith({
      id: 'issue-1',
      title: 'Updated title'
    });
  });
  it('should be able to change title', () => {
    component.issue = {
      id: '',
      key: 'DEMO-1',
      title: 'New title',
      type: IssueType.BUG,
      status: IssueStatus.ЗАДЕРЖКА,
      statusId: 'status-1',
      priority: IssuePriority.HIGH,
      listPosition: 0,
      description: '',
      estimate: 0,
      timeSpent: 0,
      timeRemaining: 0,
      createdAt: '',
      updatedAt: '',
      reporterId: '',
      authorId: '',
      userIds: [],
      comments: [],
      projectId: ''
    };
    component.ngOnChanges({
      issue: new SimpleChange(null, {title: 'New title'}, null)
    });
    expect(component.titleControl.value).toEqual('New title');
  });
  it('should not be able to change title', () => {
    component.issue = {
      id: '',
      key: 'DEMO-2',
      title: 'New title 2',
      type: IssueType.BUG,
      status: IssueStatus.ЗАДЕРЖКА,
      statusId: 'status-1',
      priority: IssuePriority.HIGH,
      listPosition: 0,
      description: '',
      estimate: 0,
      timeSpent: 0,
      timeRemaining: 0,
      createdAt: '',
      updatedAt: '',
      reporterId: '',
      authorId: '',
      userIds: [],
      comments: [],
      projectId: ''
    };

    const expected = {title: 'New title'};

    component.ngOnChanges({
      issue: new SimpleChange(expected, expected, null)
    });
    expect(component.titleControl.value).toEqual('test');
  });
});
