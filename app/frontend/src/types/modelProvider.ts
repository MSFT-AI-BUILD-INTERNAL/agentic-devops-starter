export type ModelProvider = 'github-copilot' | 'foundry';

export interface ModelProviderOption {
  id: ModelProvider;
  label: string;
}

export const MODEL_PROVIDER_OPTIONS: ModelProviderOption[] = [
  { id: 'github-copilot', label: 'GitHub Copilot' },
  { id: 'foundry', label: 'Foundry' },
];
