import { Component, OnInit } from '@angular/core';
import {
  AbstractControl,
  UntypedFormBuilder,
  UntypedFormGroup,
  ValidationErrors,
  Validators
} from '@angular/forms';
import { JCriticality, getDefaultCriticalityId } from '@trungk18/interface/criticality';
import { IssueType, JIssue } from '@trungk18/interface/issue';
import { quillConfiguration } from '@trungk18/project/config/editor';
import { NzModalRef } from 'ng-zorro-antd/modal';
import { ProjectService } from '@trungk18/project/state/project/project.service';
import { ProjectQuery } from '@trungk18/project/state/project/project.query';
import { untilDestroyed, UntilDestroy } from '@ngneat/until-destroy';
import { combineLatest, Observable } from 'rxjs';
import { JUser } from '@trungk18/interface/user';
import { map, startWith, tap } from 'rxjs/operators';
import { NoWhitespaceValidator } from '@trungk18/core/validators/no-whitespace.validator';
import { getApiErrorMessage } from '@trungk18/core/utils/api-error';
import { DateUtil } from '@trungk18/project/utils/date';

@Component({
  selector: 'add-issue-modal',
  templateUrl: './add-issue-modal.component.html',
  styleUrls: ['./add-issue-modal.component.scss']
})
@UntilDestroy()
export class AddIssueModalComponent implements OnInit {
  assignees$: Observable<JUser[]>;
  parentIssues$: Observable<JIssue[]>;
  statuses$ = this._projectQuery.statuses$;
  criticalities$ = this._projectQuery.criticalities$;
  issueForm: UntypedFormGroup;
  editorOptions = quillConfiguration;
  submitError = '';
  isSubmitting = false;
  defaultStatusId: string | null = null;
  defaultCriticalityId: string | null = null;

  get f() {
    return this.issueForm?.controls;
  }

  get canSelectParent(): boolean {
    return this.f?.type?.value === IssueType.TASK;
  }

  constructor(
    private _fb: UntypedFormBuilder,
    private _modalRef: NzModalRef,
    private _projectService: ProjectService,
    private _projectQuery: ProjectQuery
  ) {}

  ngOnInit(): void {
    this.initForm();
    this.parentIssues$ = combineLatest([
      this._projectQuery.issues$,
      this.f.type.valueChanges.pipe(startWith(this.f.type.value))
    ]).pipe(
      map(([issues, type]) =>
        type === IssueType.TASK
          ? issues.filter(
              (issue) =>
                issue.type === IssueType.EPIC ||
                issue.type === IssueType.TASK
            )
          : []
      )
    );

    this._projectQuery.statuses$
      .pipe(
        untilDestroyed(this),
        tap((statuses) => {
          const [status] = statuses;
          this.defaultStatusId = status?.id ?? null;
          if (status && !this.f.statusId.value) {
            this.f.statusId.patchValue(status.id);
          }
        })
      )
      .subscribe();

    this._projectQuery.criticalities$
      .pipe(
        untilDestroyed(this),
        tap((criticalities) => {
          this.defaultCriticalityId = getDefaultCriticalityId(criticalities);
          if (this.defaultCriticalityId && !this.f.criticalityId.value) {
            this.f.criticalityId.patchValue(this.defaultCriticalityId);
          }
        })
      )
      .subscribe();

    this.f.type.valueChanges
      .pipe(
        untilDestroyed(this),
        tap((type) => {
          if (type !== IssueType.TASK && this.f.parentId.value) {
            this.f.parentId.patchValue(null);
          }
        })
      )
      .subscribe();

    this.assignees$ = this._projectQuery.users$.pipe(
      untilDestroyed(this),
      tap(() => undefined)
    );
  }

  initForm() {
    this.issueForm = this._fb.group({
      type: [IssueType.TASK, Validators.required],
      title: ['', [Validators.required, NoWhitespaceValidator()]],
      description: [''],
      statusId: [null, Validators.required],
      criticalityId: [null],
      assigneeId: [null],
      parentId: [null],
      startDate: [null],
      dueDate: [null]
    }, {
      validators: [AddIssueModalComponent.validateDateRange]
    });
  }

  submitForm() {
    if (this.isSubmitting) {
      return;
    }

    if (this.issueForm.invalid) {
      this.issueForm.markAllAsTouched();
      return;
    }

    this.isSubmitting = true;
    this.submitError = '';
    this._projectService.createIssue({
      type: this.f.type.value,
      title: this.f.title.value,
      description: this.f.description.value,
      statusId: this.f.statusId.value,
      criticalityId: this.f.criticalityId.value ?? null,
      assigneeId: this.f.assigneeId.value ?? null,
      parentId: this.f.parentId.value ?? null,
      startDate: DateUtil.formatDateOnly(this.f.startDate.value),
      dueDate: DateUtil.formatDateOnly(this.f.dueDate.value)
    }).subscribe({
      next: () => {
        this.isSubmitting = false;
        this.resetForm();
        this.closeModal();
      },
      error: (error) => {
        this.isSubmitting = false;
        this.submitError = getApiErrorMessage(error, 'Не удалось создать задачу.');
      }
    });
  }

  cancel() {
    this.resetForm();
    this.closeModal();
  }

  closeModal() {
    this._modalRef.close();
  }

  private resetForm() {
    this.submitError = '';
    this.issueForm.reset({
      type: IssueType.TASK,
      title: '',
      description: '',
      statusId: this.defaultStatusId,
      criticalityId: this.defaultCriticalityId,
      assigneeId: null,
      parentId: null,
      startDate: null,
      dueDate: null
    });
    this.issueForm.markAsPristine();
    this.issueForm.markAsUntouched();
  }

  trackCriticality(_index: number, criticality: JCriticality): string {
    return criticality.id;
  }

  private static validateDateRange(control: AbstractControl): ValidationErrors | null {
    const startDate = DateUtil.formatDateOnly(control.get('startDate')?.value);
    const dueDate = DateUtil.formatDateOnly(control.get('dueDate')?.value);
    return DateUtil.isDateRangeInvalid(startDate, dueDate) ? { dateRange: true } : null;
  }
}
