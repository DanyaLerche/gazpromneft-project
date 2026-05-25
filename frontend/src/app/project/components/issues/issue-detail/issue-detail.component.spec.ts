import {IssueDetailComponent} from '@trungk18/project/components/issues/issue-detail/issue-detail.component';
import {IssuePriority, IssueStatus, IssueType} from '@trungk18/interface/issue';

describe('IssueDetailComponent', () => {
  let component: IssueDetailComponent;

  const projectQuery: any = {
    isCurrentUserProjectAdmin: true
  };
  const nzModalService: any = {
    create: jasmine.createSpy('create').and.callThrough()
  };
  const projectService: any = {
    updateIssue: jasmine.createSpy('updateIssue').and.callThrough(),
    deleteIssueAttachment: jasmine.createSpy('deleteIssueAttachment').and.callThrough(),
    getIssueAttachmentDownloadUrl: jasmine.createSpy('getIssueAttachmentDownloadUrl').and.callThrough(),
    listIssueAttachments: jasmine.createSpy('listIssueAttachments').and.callThrough()
  };
  const notificationService: any = {
    error: jasmine.createSpy('error').and.callThrough()
  };
  beforeEach(() => {
    component = new IssueDetailComponent(
      projectQuery,
      nzModalService,
      projectService,
      notificationService
    );
    component.issue = {
      id: '',
      key: 'DEMO-1',
      title: '',
      type: IssueType.TASK,
      status: IssueStatus.ЗАДЕРЖКА,
      statusId: 'status-1',
      priority: IssuePriority.LOW,
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
  });

  it('should be able to open Delete Issue Modal', () => {
    component.openDeleteIssueModal();
    expect(nzModalService.create).toHaveBeenCalled();
  });
  it('should be able to close Modal', () => {
    spyOn(component.onClosed, 'emit').and.callThrough();
    component.closeModal();
    expect(component.onClosed.emit).toHaveBeenCalled();
  });
  it('should be able to open Issue Page', () => {
    spyOn(component.onOpenIssue, 'emit').and.callThrough();
    component.openIssuePage();
    expect(component.onOpenIssue.emit).toHaveBeenCalled();
  });
});
