/**
 * useTheme Hook
 * 
 * React hook for accessing and managing theme state.
 * This is a wrapper around the Zustand theme store.
 */

import { useEffect } from 'react';
import { useThemeStore } from '../stores/themeStore';
import type { ThemeId, Theme } from '../types/theme';

// ============================================================================
// Hook Interface
// ============================================================================

export interface UseThemeReturn {
  /** Currently active theme ID */
  currentTheme: ThemeId;
  
  /** Full theme object for current theme */
  currentThemeObject: Theme;
  
  /** All available themes */
  availableThemes: Theme[];
  
  /** Switch to a different theme */
  setTheme: (themeId: ThemeId) => void;
  
  /** Loading state (true during initial mount) */
  isThemeLoading: boolean;
}

// ============================================================================
// Hook Implementation
// ============================================================================

/**
 * React hook for theme management.
 * 
 * Features:
 * - Access current theme
 * - Switch themes
 * - List available themes
 * - Automatic persistence via localStorage
 * 
 * @returns Theme state and actions
 * 
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { currentTheme, setTheme, availableThemes } = useTheme();
 *   
 *   return (
 *     <select value={currentTheme} onChange={e => setTheme(e.target.value as ThemeId)}>
 *       {availableThemes.map(theme => (
 *         <option key={theme.id} value={theme.id}>{theme.name}</option>
 *       ))}
 *     </select>
 *   );
 * }
 * ```
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
  
  // Get current theme object
  const currentThemeObject = getCurrentThemeObject();
  
  return {
    currentTheme,
    currentThemeObject,
    availableThemes,
    setTheme,
    isThemeLoading: isLoading,
  };
}

// ============================================================================
// Additional Hooks
// ============================================================================

/**
 * Hook to get only the current theme ID.
 * Lightweight alternative when you don't need the full theme object.
 * 
 * @returns Current theme ID
 * 
 * @example
 * ```tsx
 * function MyComponent() {
 *   const themeId = useCurrentTheme();
 *   return <div data-theme={themeId}>...</div>;
 * }
 * ```
 */
export function useCurrentTheme(): ThemeId {
  return useThemeStore((state: any) => state.currentTheme);
}

/**
 * Hook to get the theme setter function.
 * Useful when you only need to change the theme, not read it.
 * 
 * @returns Theme setter function
 * 
 * @example
 * ```tsx
 * function ThemeToggle() {
 *   const setTheme = useSetTheme();
 *   return <button onClick={() => setTheme('dark')}>Dark Mode</button>;
 * }
 * ```
 */
export function useSetTheme(): (themeId: ThemeId) => void {
  return useThemeStore((state: any) => state.setTheme);
}

/**
 * Hook to get all available themes.
 * 
 * @returns Array of available themes
 */
export function useAvailableThemes(): Theme[] {
  return useThemeStore((state: any) => state.availableThemes);
}
