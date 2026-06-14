import { useModelProviderStore } from '../stores/modelProviderStore';
import { MODEL_PROVIDER_OPTIONS, type ModelProvider } from '../types/modelProvider';

export function ModelSelector() {
  const selectedProvider = useModelProviderStore((state) => state.selectedProvider);
  const setSelectedProvider = useModelProviderStore((state) => state.setSelectedProvider);

  return (
    <label className="flex items-center gap-2 px-3 py-2 rounded-lg bg-secondary border border-border text-text-primary">
      <span className="text-sm font-medium hidden sm:inline">Model</span>
      <select
        value={selectedProvider}
        onChange={(event) => setSelectedProvider(event.target.value as ModelProvider)}
        className="bg-secondary text-sm font-medium text-text-primary focus:outline-none focus:ring-2 focus:ring-border-focus rounded"
        aria-label="Model selector"
      >
        {MODEL_PROVIDER_OPTIONS.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
