import { useMemo } from 'react';
import { useTheme } from '../hooks/useTheme';
import { SelectionDropdown } from './SelectionDropdown';

export function ThemeSelector() {
  const { currentTheme, currentThemeObject, availableThemes, setTheme } = useTheme();
  const themeOptions = useMemo(
    () =>
      availableThemes.map((theme) => ({
        id: theme.id,
        label: theme.name,
        description: theme.description,
      })),
    [availableThemes]
  );

  return (
    <SelectionDropdown
      ariaLabel={`Theme selector. Current theme: ${currentThemeObject.name}`}
      buttonText={currentThemeObject.name}
      icon={
        <svg
          className="h-5 w-5 text-text-primary"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
          />
        </svg>
      }
      listboxLabel="Available themes"
      onSelect={setTheme}
      optionIdPrefix="theme-option"
      options={themeOptions}
      selectedId={currentTheme}
    />
  );
}
