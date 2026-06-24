import { describe, expect, it } from 'vitest';
import type { SelectionOption } from './SelectionDropdown';
import { getSelectedOptionIndex, getWrappedOptionIndex } from './SelectionDropdown.utils';

const options: SelectionOption<string>[] = [
  { id: 'one', label: 'One', description: 'First option' },
  { id: 'two', label: 'Two', description: 'Second option' },
  { id: 'three', label: 'Three', description: 'Third option' },
];

describe('SelectionDropdown helpers', () => {
  it('finds the selected option index', () => {
    expect(getSelectedOptionIndex(options, 'two')).toBe(1);
    expect(getSelectedOptionIndex(options, 'three')).toBe(2);
  });

  it('returns -1 when the selected option is missing', () => {
    expect(getSelectedOptionIndex(options, 'missing')).toBe(-1);
  });

  it('wraps option indices in both directions', () => {
    expect(getWrappedOptionIndex(3, options.length)).toBe(0);
    expect(getWrappedOptionIndex(-1, options.length)).toBe(2);
    expect(getWrappedOptionIndex(1, options.length)).toBe(1);
  });

  it('returns -1 when there are no options', () => {
    expect(getWrappedOptionIndex(0, 0)).toBe(-1);
  });
});
