import type { SelectionOption } from './SelectionDropdown';

export function getSelectedOptionIndex<T extends string>(
  options: ReadonlyArray<SelectionOption<T>>,
  selectedId: T
): number {
  return options.findIndex((option) => option.id === selectedId);
}

export function getWrappedOptionIndex(index: number, optionCount: number): number {
  if (optionCount <= 0) {
    return -1;
  }

  return ((index % optionCount) + optionCount) % optionCount;
}
