/**
 * Theme System Type Definitions
 * 
 * Core types for the chat theme selector feature.
 */

// ============================================================================
// Core Types
// ============================================================================

/** Theme identifier */
export type ThemeId = 'light' | 'dark' | 'high-contrast';

/** Color palette for a theme */
export interface ThemeColors {
  bgPrimary: string;
  bgSecondary: string;
  bgTertiary: string;
  textPrimary: string;
  textSecondary: string;
  textInverse: string;
  accent: string;
  accentHover: string;
  accentLight: string;
  border: string;
  borderFocus: string;
  messageBubbleUser: string;
  messageBubbleUserText: string;
  messageBubbleAssistant: string;
  messageBubbleAssistantText: string;
  messageBubbleTool: string;
  messageBubbleToolText: string;
  success: string;
  error: string;
  warning: string;
  info: string;
  hoverOverlay: string;
  activeOverlay: string;
}

/** Theme metadata */
export interface ThemeMetadata {
  contrastRatios: {
    normalText: number;
    largeText: number;
    uiComponents: number;
  };
  version: string;
  wcagLevel: 'AA' | 'AAA';
  author?: string;
  tags?: string[];
}

/** Complete theme definition */
export interface Theme {
  id: ThemeId;
  name: string;
  description: string;
  colors: ThemeColors;
  metadata: ThemeMetadata;
}

/** Global theme configuration */
export interface ThemeConfig {
  themes: Theme[];
  defaultTheme: ThemeId;
  storageKey: string;
  allowCustomThemes: boolean;
}

// ============================================================================
// Type Guards
// ============================================================================

/** Check if a value is a valid ThemeId */
export function isValidThemeId(value: unknown): value is ThemeId {
  return typeof value === 'string' && 
         ['light', 'dark', 'high-contrast'].includes(value);
}
