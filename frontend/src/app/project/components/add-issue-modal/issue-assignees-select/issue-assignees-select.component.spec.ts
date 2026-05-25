import { IssueAssigneesSelectComponent } from '@trungk18/project/components/add-issue-modal/issue-assignees-select/issue-assignees-select.component';

describe('IssueAssigneesSelectComponent', () => {
  let component: IssueAssigneesSelectComponent;

  beforeEach(() => {
    component = new IssueAssigneesSelectComponent();
    component.users = [
      {
        id: 'test',
        name: '',
        email: '',
        avatarUrl: '',
        createdAt: '',
        updatedAt: '',
        issueIds: []
      }
    ];
  });

  it('stores provided users', () => {
    expect(component.users[0].id).toEqual('test');
  });
});
