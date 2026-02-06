/**
 * useTheme Hook
 * 
 * React hook for accessing and managing theme state.
 */

import { useEffect } from 'react';
import { useThemeStore } from '../stores/themeStore';
import type { ThemeId, Theme } from '../types/theme';

export interface UseThemeReturn {
  currentTheme: ThemeId;
  currentThemeObject: Theme;
  availableThemes: Theme[];
  setTheme: (themeId: ThemeId) => void;
  isThemeLoading: boolean;
}

/**
 * React hook for theme management.
 */
export function useTheme(): UseThemeReturn {
  const currentTheme = useThemeStore((state) => state.currentTheme);
  const availableThemes = useThemeStore((state) => state.availableThemes);
  const setTheme = useThemeStore((state) => state.setTheme);
  const isLoading = useThemeStore((state) => state.isLoading);
  const initializeTheme = useThemeStore((state) => state.initializeTheme);
  const getCurrentThemeObject = useThemeStore((state) => state.getCurrentThemeObject);
  
  // Initialize theme on mount
  useEffect(() => {
    initializeTheme();
  }, [initializeTheme]);
  
  return {
    currentTheme,
    currentThemeObject: getCurrentThemeObject(),
    availableThemes,
    setTheme,
    isThemeLoading: isLoading,
  };
}
