import {
  Component,
  ElementRef,
  EventEmitter,
  forwardRef,
  HostBinding,
  HostListener,
  Input,
  Output,
  TemplateRef
} from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';

@Component({
  selector: 'project-inline-select',
  templateUrl: './inline-select.component.html',
  styleUrls: ['./inline-select.component.scss'],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => InlineSelectComponent),
      multi: true
    }
  ]
})
export class InlineSelectComponent implements ControlValueAccessor {
  @Input() items: any[] | null = [];
  @Input() labelKey = 'label';
  @Input() valueKey = 'value';
  @Input() placeholder = '';
  @Input() allowClear = false;
  @Input() multiple = false;
  @Input() disabled = false;
  @Input() appearance: 'field' | 'button' | 'link' = 'field';
  @Input() emptyText = 'Нет вариантов';
  @Input() triggerClassName = '';
  @Input() showSelectedValue = true;
  @Input() selectedTemplate?: TemplateRef<any>;
  @Input() optionTemplate?: TemplateRef<any>;
  @Output() selectionChange = new EventEmitter<any>();

  @HostBinding('class.project-inline-select-host--compact')
  get isCompactHost(): boolean {
    return this.appearance !== 'field';
  }

  isOpen = false;
  private value: any = null;
  private onChange: (value: any) => void = () => undefined;
  private onTouched: () => void = () => undefined;

  constructor(private readonly elementRef: ElementRef<HTMLElement>) {}

  get triggerClasses(): string[] {
    const appearanceClass =
      this.appearance === 'field'
        ? 'project-inline-select__trigger--field'
        : this.appearance === 'button'
          ? 'project-inline-select__trigger--button'
          : 'project-inline-select__trigger--link';

    return [
      'project-inline-select__trigger',
      appearanceClass,
      ...this.triggerClassName.split(' ').filter(Boolean)
    ];
  }

  get visibleItems(): any[] {
    return this.items ?? [];
  }

  get selectedItems(): any[] {
    if (this.multiple) {
      const selectedValues = this.getSelectedValues();
      return this.visibleItems.filter((item) => selectedValues.some((value) => this.isSameValue(value, this.getItemValue(item))));
    }

    const selectedItem = this.visibleItems.find((item) => this.isSameValue(this.value, this.getItemValue(item)));
    return selectedItem ? [selectedItem] : [];
  }

  get hasSelection(): boolean {
    return this.selectedItems.length > 0;
  }

  get displayValue(): string {
    if (!this.hasSelection || !this.showSelectedValue) {
      return this.placeholder;
    }

    const labels = this.selectedItems
      .map((item) => this.getItemLabel(item))
      .filter((label): label is string => !!label);

    if (!labels.length) {
      return this.placeholder;
    }

    return this.multiple ? labels.join(', ') : labels[0];
  }

  toggleOpen(): void {
    if (this.disabled) {
      return;
    }

    this.isOpen = !this.isOpen;
  }

  close(): void {
    if (!this.isOpen) {
      return;
    }

    this.isOpen = false;
    this.onTouched();
  }

  clear(event: MouseEvent): void {
    event.stopPropagation();

    const nextValue = this.multiple ? [] : null;
    this.writeInternalValue(nextValue);
    this.onChange(nextValue);
    this.selectionChange.emit(nextValue);
  }

  selectItem(item: any): void {
    if (this.disabled || this.isItemDisabled(item)) {
      return;
    }

    const itemValue = this.getItemValue(item);

    if (this.multiple) {
      const selectedValues = this.getSelectedValues();
      const nextValue = this.isItemSelected(item)
        ? selectedValues.filter((value) => !this.isSameValue(value, itemValue))
        : [...selectedValues, itemValue];

      this.writeInternalValue(nextValue);
      this.onChange(nextValue);
      this.selectionChange.emit(nextValue);
      return;
    }

    this.writeInternalValue(itemValue);
    this.onChange(itemValue);
    this.selectionChange.emit(itemValue);
    this.close();
  }

  isItemSelected(item: any): boolean {
    const itemValue = this.getItemValue(item);

    if (this.multiple) {
      return this.getSelectedValues().some((value) => this.isSameValue(value, itemValue));
    }

    return this.isSameValue(this.value, itemValue);
  }

  isItemDisabled(item: any): boolean {
    return !!item?.disabled;
  }

  getOptionContext(item: any): Record<string, unknown> {
    return {
      $implicit: item,
      selected: this.isItemSelected(item)
    };
  }

  getSelectedContext(): Record<string, unknown> {
    return {
      $implicit: this.multiple ? this.selectedItems : this.selectedItems[0],
      items: this.selectedItems
    };
  }

  trackByValue = (_index: number, item: any): any => this.getItemValue(item);

  writeValue(value: any): void {
    this.writeInternalValue(value);
  }

  registerOnChange(fn: (value: any) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    this.disabled = isDisabled;
    if (isDisabled) {
      this.close();
    }
  }

  @HostListener('document:mousedown', ['$event'])
  onDocumentMouseDown(event: MouseEvent): void {
    const target = event.target as Node | null;
    if (!target || this.elementRef.nativeElement.contains(target)) {
      return;
    }

    this.close();
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.close();
  }

  private writeInternalValue(value: any): void {
    if (this.multiple) {
      this.value = Array.isArray(value) ? [...value] : [];
      return;
    }

    this.value = value ?? null;
  }

  private getSelectedValues(): any[] {
    return Array.isArray(this.value) ? this.value : [];
  }

  getItemValue(item: any): any {
    if (item == null || !this.valueKey) {
      return item;
    }

    return item[this.valueKey];
  }

  getItemLabel(item: any): string {
    if (item == null) {
      return '';
    }

    if (!this.labelKey) {
      return String(item);
    }

    const label = item[this.labelKey];
    return label == null ? '' : String(label);
  }

  private isSameValue(left: any, right: any): boolean {
    return left === right;
  }
}
