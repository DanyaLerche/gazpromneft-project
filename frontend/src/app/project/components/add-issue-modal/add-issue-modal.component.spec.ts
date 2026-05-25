import { AddIssueModalComponent } from '@trungk18/project/components/add-issue-modal/add-issue-modal.component';
import { IssueType } from '@trungk18/interface/issue';
import { of } from 'rxjs';

describe('AddIssueModalComponent', () => {
  let component: AddIssueModalComponent;
  let formGroup: any;

  const formBuilder: any = {
    group: jasmine.createSpy('group')
  };
  const nzModalRef: any = {
    close: jasmine.createSpy('close').and.callThrough()
  };
  const projectService: any = {
    createIssue: jasmine.createSpy('createIssue').and.returnValue(of({}))
  };
  const projectQuery: any = {};

  beforeEach(() => {
    formGroup = {
      invalid: false,
      controls: {
        type: { value: IssueType.TASK },
        title: { value: 'Новая задача' },
        description: { value: '' },
        statusId: { value: 'status-1' },
        criticalityId: { value: null },
        assigneeId: { value: null },
        parentId: { value: null },
        startDate: { value: null },
        dueDate: { value: null }
      },
      reset: jasmine.createSpy('reset').and.callThrough(),
      markAsPristine: jasmine.createSpy('markAsPristine').and.callThrough(),
      markAsUntouched: jasmine.createSpy('markAsUntouched').and.callThrough(),
      markAllAsTouched: jasmine.createSpy('markAllAsTouched').and.callThrough()
    };
    formBuilder.group.and.returnValue(formGroup);

    component = new AddIssueModalComponent(
      formBuilder,
      nzModalRef,
      projectService,
      projectQuery
    );
  });

  it('should be able to initForm', () => {
    component.initForm();
    expect(formBuilder.group).toHaveBeenCalled();
  });
  it('should be able to submit Form', () => {
    component.initForm();
    component.submitForm();
    expect(projectService.createIssue).toHaveBeenCalledWith({
      type: IssueType.TASK,
      title: 'Новая задача',
      description: '',
      statusId: 'status-1',
      criticalityId: null,
      assigneeId: null,
      parentId: null,
      startDate: null,
      dueDate: null
    });
    expect(nzModalRef.close).toHaveBeenCalled();
    expect(formBuilder.group).toHaveBeenCalled();
  });
});
