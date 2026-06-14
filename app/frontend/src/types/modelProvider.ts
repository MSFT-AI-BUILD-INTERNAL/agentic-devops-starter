export type ModelProvider = 'github-copilot' | 'foundry';

export interface ModelProviderOption {
  id: ModelProvider;
  label: string;
  description: string;
}

export const MODEL_PROVIDER_OPTIONS: ModelProviderOption[] = [
  {
    id: 'github-copilot',
    label: 'GitHub Copilot',
    description: 'Default GitHub Copilot model provider',
  },
  {
    id: 'foundry',
    label: 'Microsoft Foundry',
    description: 'Use your Azure AI Foundry deployment',
  },
];
