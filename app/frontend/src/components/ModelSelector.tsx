import { useCallback, useEffect, useRef, useState } from 'react';
import { useModelProviderStore } from '../stores/modelProviderStore';
import { MODEL_PROVIDER_OPTIONS, type ModelProvider } from '../types/modelProvider';

export function ModelSelector() {
  const selectedProvider = useModelProviderStore((state) => state.selectedProvider);
  const setSelectedProvider = useModelProviderStore((state) => state.setSelectedProvider);
  const [isOpen, setIsOpen] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(0);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const handleModelSelect = useCallback((provider: ModelProvider) => {
    setSelectedProvider(provider);
    setIsOpen(false);
    buttonRef.current?.focus();
  }, [setSelectedProvider]);

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

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (!isOpen) return;

      switch (event.key) {
        case 'ArrowDown':
          event.preventDefault();
          setFocusedIndex((prev) => (prev + 1) % MODEL_PROVIDER_OPTIONS.length);
          break;
        case 'ArrowUp':
          event.preventDefault();
          setFocusedIndex((prev) => (
            prev - 1 + MODEL_PROVIDER_OPTIONS.length
          ) % MODEL_PROVIDER_OPTIONS.length);
          break;
        case 'Enter':
        case ' ':
          event.preventDefault();
          handleModelSelect(MODEL_PROVIDER_OPTIONS[focusedIndex].id);
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
          setFocusedIndex(MODEL_PROVIDER_OPTIONS.length - 1);
          break;
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, focusedIndex, handleModelSelect]);

  const selectedOption = MODEL_PROVIDER_OPTIONS.find((option) => option.id === selectedProvider);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        ref={buttonRef}
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg bg-secondary border border-border hover:bg-tertiary focus:outline-none focus:ring-2 focus:ring-border-focus transition-colors"
        aria-label={`Model selector. Current model: ${selectedOption?.label || 'Unknown'}`}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        type="button"
      >
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
            d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
          />
        </svg>

        <span className="text-sm font-medium text-text-primary hidden sm:inline">
          {selectedOption?.label || 'Model'}
        </span>

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

      {isOpen && (
        <div
          className="absolute right-0 mt-2 w-64 bg-primary border border-border rounded-lg shadow-lg z-50"
          role="listbox"
          aria-label="Available models"
          aria-activedescendant={`model-option-${MODEL_PROVIDER_OPTIONS[focusedIndex]?.id}`}
        >
          {MODEL_PROVIDER_OPTIONS.map((option, index) => (
            <button
              key={option.id}
              id={`model-option-${option.id}`}
              onClick={() => handleModelSelect(option.id)}
              onMouseEnter={() => setFocusedIndex(index)}
              className={`w-full text-left px-4 py-3 hover:bg-secondary focus:bg-secondary focus:outline-none transition-colors first:rounded-t-lg last:rounded-b-lg ${
                option.id === selectedProvider ? 'bg-accent-light' : ''
              } ${index === focusedIndex ? 'bg-secondary' : ''}`}
              role="option"
              aria-selected={option.id === selectedProvider}
              tabIndex={-1}
              type="button"
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-text-primary">{option.label}</div>
                  <div className="text-sm text-text-secondary mt-0.5">
                    {option.description}
                  </div>
                </div>

                {option.id === selectedProvider && (
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
