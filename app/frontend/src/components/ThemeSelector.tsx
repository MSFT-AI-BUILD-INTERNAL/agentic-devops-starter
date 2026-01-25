/**
 * ThemeSelector Component
 * 
 * Dropdown UI for selecting between available themes.
 * Provides accessible theme switching with keyboard navigation.
 */

import { useState, useRef, useEffect } from 'react';
import { useTheme } from '../hooks/useTheme';
import type { ThemeId } from '../types/theme';

export function ThemeSelector() {
  const { currentTheme, availableThemes, setTheme } = useTheme();
  const [isOpen, setIsOpen] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(0);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  
  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);
  
  // Keyboard navigation
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (!isOpen) return;
      
      switch (event.key) {
        case 'ArrowDown':
          event.preventDefault();
          setFocusedIndex((prev) => (prev + 1) % availableThemes.length);
          break;
        case 'ArrowUp':
          event.preventDefault();
          setFocusedIndex((prev) => (prev - 1 + availableThemes.length) % availableThemes.length);
          break;
        case 'Enter':
        case ' ':
          event.preventDefault();
          handleThemeSelect(availableThemes[focusedIndex].id);
          break;
        case 'Escape':
          event.preventDefault();
          setIsOpen(false);
          buttonRef.current?.focus();
          break;
        case 'Home':
          event.preventDefault();
          setFocusedIndex(0);
          break;
        case 'End':
          event.preventDefault();
          setFocusedIndex(availableThemes.length - 1);
          break;
      }
    }
    
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, focusedIndex, availableThemes]);
  
  // Handle theme selection
  const handleThemeSelect = (themeId: ThemeId) => {
    setTheme(themeId);
    setIsOpen(false);
    buttonRef.current?.focus();
  };
  
  // Get current theme object
  const currentThemeObject = availableThemes.find(t => t.id === currentTheme);
  
  return (
    <div className="relative" ref={dropdownRef}>
      {/* Theme Selector Button */}
      <button
        ref={buttonRef}
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg bg-secondary border border-border hover:bg-tertiary focus:outline-none focus:ring-2 focus:ring-border-focus transition-colors"
        aria-label={`Theme selector. Current theme: ${currentThemeObject?.name || 'Unknown'}`}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        type="button"
      >
        {/* Theme Icon */}
        <svg
          className="w-5 h-5 text-text-primary"
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
        
        {/* Current Theme Name */}
        <span className="text-sm font-medium text-text-primary hidden sm:inline">
          {currentThemeObject?.name || 'Theme'}
        </span>
        
        {/* Dropdown Arrow */}
        <svg
          className={`w-4 h-4 text-text-secondary transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      
      {/* Dropdown Menu */}
      {isOpen && (
        <div
          className="absolute right-0 mt-2 w-64 bg-primary border border-border rounded-lg shadow-lg z-50"
          role="listbox"
          aria-label="Available themes"
          aria-activedescendant={`theme-option-${availableThemes[focusedIndex]?.id}`}
        >
          {availableThemes.map((theme, index) => (
            <button
              key={theme.id}
              id={`theme-option-${theme.id}`}
              onClick={() => handleThemeSelect(theme.id)}
              onMouseEnter={() => setFocusedIndex(index)}
              className={`w-full text-left px-4 py-3 hover:bg-secondary focus:bg-secondary focus:outline-none transition-colors first:rounded-t-lg last:rounded-b-lg ${
                theme.id === currentTheme ? 'bg-accent-light' : ''
              } ${index === focusedIndex ? 'bg-secondary' : ''}`}
              role="option"
              aria-selected={theme.id === currentTheme}
              tabIndex={-1}
              type="button"
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-text-primary">{theme.name}</div>
                  <div className="text-sm text-text-secondary mt-0.5">
                    {theme.description}
                  </div>
                </div>
                
                {/* Selected Indicator */}
                {theme.id === currentTheme && (
                  <svg
                    className="w-5 h-5 text-accent"
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
