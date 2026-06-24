import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { getSelectedOptionIndex, getWrappedOptionIndex } from './SelectionDropdown.utils';

export interface SelectionOption<T extends string> {
  id: T;
  label: string;
  description: string;
}

interface SelectionDropdownProps<T extends string> {
  ariaLabel: string;
  buttonText: string;
  icon: ReactNode;
  listboxLabel: string;
  onSelect: (id: T) => void;
  optionIdPrefix: string;
  options: ReadonlyArray<SelectionOption<T>>;
  selectedId: T;
}

export function SelectionDropdown<T extends string>({
  ariaLabel,
  buttonText,
  icon,
  listboxLabel,
  onSelect,
  optionIdPrefix,
  options,
  selectedId,
}: SelectionDropdownProps<T>) {
  const [isOpen, setIsOpen] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(() => getSelectedOptionIndex(options, selectedId));
  const dropdownRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const selectedIndex = getSelectedOptionIndex(options, selectedId);
  const selectedOption = selectedIndex >= 0 ? options[selectedIndex] : undefined;

  const closeDropdown = useCallback((restoreFocus: boolean) => {
    setIsOpen(false);

    if (restoreFocus) {
      buttonRef.current?.focus();
    }
  }, []);

  const handleSelect = useCallback(
    (id: T) => {
      onSelect(id);
      closeDropdown(true);
    },
    [closeDropdown, onSelect]
  );

  const handleToggle = useCallback(() => {
    setIsOpen((previous) => !previous);
  }, []);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    setFocusedIndex(selectedIndex >= 0 ? selectedIndex : 0);
  }, [isOpen, selectedIndex]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        closeDropdown(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (options.length === 0) {
        return;
      }

      switch (event.key) {
        case 'ArrowDown':
          event.preventDefault();
          setFocusedIndex((previous) => getWrappedOptionIndex(previous + 1, options.length));
          break;
        case 'ArrowUp':
          event.preventDefault();
          setFocusedIndex((previous) => getWrappedOptionIndex(previous - 1, options.length));
          break;
        case 'Enter':
        case ' ':
          event.preventDefault();
          handleSelect(options[focusedIndex >= 0 ? focusedIndex : 0].id);
          break;
        case 'Escape':
          event.preventDefault();
          closeDropdown(true);
          break;
        case 'Home':
          event.preventDefault();
          setFocusedIndex(0);
          break;
        case 'End':
          event.preventDefault();
          setFocusedIndex(options.length - 1);
          break;
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [closeDropdown, focusedIndex, handleSelect, isOpen, options]);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        ref={buttonRef}
        onClick={handleToggle}
        className="flex items-center gap-2 rounded-lg border border-border bg-secondary px-3 py-2 transition-colors hover:bg-tertiary focus:outline-none focus:ring-2 focus:ring-border-focus"
        aria-label={ariaLabel}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        type="button"
      >
        {icon}

        <span className="hidden text-sm font-medium text-text-primary sm:inline">
          {selectedOption?.label ?? buttonText}
        </span>

        <svg
          className={`h-4 w-4 text-text-secondary transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div
          className="absolute right-0 z-50 mt-2 w-64 rounded-lg border border-border bg-primary shadow-lg"
          role="listbox"
          aria-label={listboxLabel}
          aria-activedescendant={
            focusedIndex >= 0 ? `${optionIdPrefix}-${options[focusedIndex]?.id}` : undefined
          }
        >
          {options.map((option, index) => (
            <button
              key={option.id}
              id={`${optionIdPrefix}-${option.id}`}
              onClick={() => handleSelect(option.id)}
              onMouseEnter={() => setFocusedIndex(index)}
              className={`first:rounded-t-lg last:rounded-b-lg w-full px-4 py-3 text-left transition-colors hover:bg-secondary focus:bg-secondary focus:outline-none ${
                option.id === selectedId ? 'bg-accent-light' : ''
              } ${index === focusedIndex ? 'bg-secondary' : ''}`}
              role="option"
              aria-selected={option.id === selectedId}
              tabIndex={-1}
              type="button"
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-text-primary">{option.label}</div>
                  <div className="mt-0.5 text-sm text-text-secondary">{option.description}</div>
                </div>

                {option.id === selectedId && (
                  <svg
                    className="h-5 w-5 text-accent"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                    aria-label="Currently selected"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                )}
              </div>
            </button>
          ))}
        </div>
      )}

    </div>
  );
}
