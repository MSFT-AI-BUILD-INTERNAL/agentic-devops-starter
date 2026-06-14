import { create } from 'zustand';
import type { ModelProvider } from '../types/modelProvider';

interface ModelProviderStore {
  selectedProvider: ModelProvider;
  setSelectedProvider: (provider: ModelProvider) => void;
}

export const useModelProviderStore = create<ModelProviderStore>((set) => ({
  selectedProvider: 'github-copilot',
  setSelectedProvider: (provider) => set({ selectedProvider: provider }),
}));
