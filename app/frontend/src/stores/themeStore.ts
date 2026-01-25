/**
 * Theme Store (Zustand)
 * 
 * Global state management for theme system with localStorage persistence.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ThemeId, Theme } from '../types/theme';
import { themeConfig } from '../config/themes';
import { isValidThemeId } from '../types/theme';
import { applyThemeToDocument } from '../utils/themeUtils';

// ============================================================================
// Store Interface
// ============================================================================

interface ThemeStore {
  // State
  currentTheme: ThemeId;
  availableThemes: Theme[];
  isLoading: boolean;
  
  // Actions
  setTheme: (themeId: ThemeId) => void;
  initializeTheme: () => void;
  
  // Computed
  getCurrentThemeObject: () => Theme;
}

// ============================================================================
// Store Implementation
// ============================================================================

/**
 * Theme store with localStorage persistence.
 * 
 * Usage:
 * ```typescript
 * const { currentTheme, setTheme } = useThemeStore();
 * setTheme('dark');
 * ```
 */
export const useThemeStore = create<ThemeStore>()(
  persist(
    (set, get) => ({
      // Initial state
      currentTheme: themeConfig.defaultTheme,
      availableThemes: themeConfig.themes,
      isLoading: true,
      
      // Actions
      setTheme: (themeId: ThemeId) => {
        // Validate theme ID
        if (!isValidThemeId(themeId)) {
          console.error(`Invalid theme ID: ${themeId}`);
          return;
        }
        
        // Update state
        set({ currentTheme: themeId });
        
        // Apply theme to document
        applyThemeToDocument(themeId);
        
        // Log theme change
        console.log(`Theme changed to: ${themeId}`);
      },
      
      initializeTheme: () => {
        const { currentTheme } = get();
        
        // Apply theme to document on mount
        applyThemeToDocument(currentTheme);
        
        // Mark as loaded
        set({ isLoading: false });
        
        console.log(`Theme initialized: ${currentTheme}`);
      },
      
      // Computed values
      getCurrentThemeObject: () => {
        const { currentTheme, availableThemes } = get();
        const theme = availableThemes.find((t) => t.id === currentTheme);
        return theme || availableThemes[0]; // Fallback to first theme
      },
    }),
    {
      name: themeConfig.storageKey, // localStorage key
      
      // Custom storage implementation with error handling
      storage: {
        getItem: (name: string) => {
          try {
            const value = localStorage.getItem(name);
            return value ? JSON.parse(value) : null;
          } catch (error) {
            console.warn('localStorage is unavailable:', error);
            return null;
          }
        },
        setItem: (name: string, value: unknown) => {
          try {
            localStorage.setItem(name, JSON.stringify(value));
          } catch (error) {
            console.warn('Failed to save theme preference:', error);
          }
        },
        removeItem: (name: string) => {
          try {
            localStorage.removeItem(name);
          } catch (error) {
            console.warn('Failed to remove theme preference:', error);
          }
        },
      },
      
      // Only persist currentTheme (not computed values)
      partialize: (state) => ({
        currentTheme: state.currentTheme,
      }),
      
      // Migrate old data if needed
      version: 1,
      migrate: (persistedState: unknown, version: number) => {
        if (version === 0) {
          // Migrate from old format (if needed in future)
          return persistedState as ThemeStore;
        }
        return persistedState as ThemeStore;
      },
      
      // Merge persisted state with default state
      merge: (persistedState, currentState) => {
        const merged = { 
          ...currentState, 
          ...(persistedState && typeof persistedState === 'object' ? persistedState : {})
        };
        
        // Validate persisted theme ID
        if (persistedState && typeof persistedState === 'object' && 'currentTheme' in persistedState) {
          const themeId = (persistedState as { currentTheme: unknown }).currentTheme;
          if (!isValidThemeId(themeId)) {
            console.warn(`Invalid persisted theme ID: ${themeId}, using default`);
            merged.currentTheme = themeConfig.defaultTheme;
          }
        }
        
        return merged;
      },
    }
  )
);

// ============================================================================
// Store Utilities
// ============================================================================

/**
 * Get current theme ID without subscribing to store updates.
 * Useful for one-time reads.
 */
export function getCurrentThemeId(): ThemeId {
  return useThemeStore.getState().currentTheme;
}

/**
 * Get current theme object without subscribing to store updates.
 */
export function getCurrentTheme(): Theme {
  return useThemeStore.getState().getCurrentThemeObject();
}

/**
 * Set theme without using React hook.
 * Useful for non-React code.
 */
export function setGlobalTheme(themeId: ThemeId): void {
  useThemeStore.getState().setTheme(themeId);
}
