import { useModelProviderStore } from '../stores/modelProviderStore';
import { MODEL_PROVIDER_OPTIONS, type ModelProvider } from '../types/modelProvider';
import { SelectionDropdown } from './SelectionDropdown';

export function ModelSelector() {
  const selectedProvider = useModelProviderStore((state) => state.selectedProvider);
  const setSelectedProvider = useModelProviderStore((state) => state.setSelectedProvider);

  const handleModelSelect = (provider: ModelProvider) => {
    setSelectedProvider(provider);
  };

  const selectedOption = MODEL_PROVIDER_OPTIONS.find((option) => option.id === selectedProvider);

  return (
    <SelectionDropdown
      ariaLabel={`Model selector. Current model: ${selectedOption?.label || 'Unknown'}`}
      buttonText={selectedOption?.label || 'Model'}
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
            d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
          />
        </svg>
      }
      listboxLabel="Available models"
      onSelect={handleModelSelect}
      optionIdPrefix="model-option"
      options={MODEL_PROVIDER_OPTIONS}
      selectedId={selectedProvider}
    />
  );
}
