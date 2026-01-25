/**
 * Theme System Type Definitions
 * 
 * This file contains all TypeScript interfaces, types, and utilities for the
 * chat theme selector feature. These types define the contract between the
 * theme system and consuming components.
 * 
 * @module theme-types
 * @version 1.0.0
 */

// ============================================================================
// Core Types
// ============================================================================

/**
 * Unique identifier for a theme variant.
 * Extensible via string literal union.
 */
export type ThemeId = 'light' | 'dark' | 'high-contrast';

/**
 * WCAG conformance level for accessibility compliance.
 */
export type WCAGLevel = 'AA' | 'AAA';

// ============================================================================
// Color Palette
// ============================================================================

/**
 * Complete color palette for a theme.
 * All colors must be valid CSS color values (hex, rgb, hsl).
 * 
 * @remarks
 * Colors are semantic (purpose-based) rather than literal (e.g., "blue").
 * This allows themes to use different color schemes while maintaining
 * consistent UI semantics.
 */
export interface ThemeColors {
  // Background colors
  /** Main application background */
  bgPrimary: string;
  /** Secondary surfaces (cards, panels) */
  bgSecondary: string;
  /** Tertiary backgrounds (hover states, subtle highlights) */
  bgTertiary: string;
  
  // Text colors
  /** Primary body text */
  textPrimary: string;
  /** Secondary/muted text (descriptions, timestamps) */
  textSecondary: string;
  /** Text on colored backgrounds (e.g., buttons) */
  textInverse: string;
  
  // Accent colors
  /** Primary brand/accent color */
  accent: string;
  /** Accent hover state */
  accentHover: string;
  /** Light accent for backgrounds */
  accentLight: string;
  
  // UI element colors
  /** Borders and dividers */
  border: string;
  /** Focus ring color (keyboard navigation) */
  borderFocus: string;
  
  // Message bubble colors
  /** User message background */
  messageBubbleUser: string;
  /** User message text */
  messageBubbleUserText: string;
  /** Assistant message background */
  messageBubbleAssistant: string;
  /** Assistant message text */
  messageBubbleAssistantText: string;
  /** Tool/system message background */
  messageBubbleTool: string;
  /** Tool/system message text */
  messageBubbleToolText: string;
  
  // Status colors
  /** Success state (confirmations, completed actions) */
  success: string;
  /** Error state (failures, validation errors) */
  error: string;
  /** Warning state (cautions, non-critical issues) */
  warning: string;
  /** Info state (neutral information) */
  info: string;
  
  // Interactive states
  /** Semi-transparent overlay for hover states */
  hoverOverlay: string;
  /** Semi-transparent overlay for active/pressed states */
  activeOverlay: string;
}

// ============================================================================
// Accessibility Metadata
// ============================================================================

/**
 * Measured contrast ratios for accessibility validation.
 * 
 * @remarks
 * - Normal text: 4.5:1 minimum (WCAG AA), 7.0:1 recommended (WCAG AAA)
 * - Large text (≥18pt or 14pt bold): 3.0:1 minimum (AA), 4.5:1 recommended (AAA)
 * - UI components: 3.0:1 minimum (AA)
 */
export interface ContrastRatios {
  /** Contrast ratio for normal text vs primary background */
  normalText: number;
  /** Contrast ratio for large text vs primary background */
  largeText: number;
  /** Contrast ratio for UI components (borders, icons) vs background */
  uiComponents: number;
}

/**
 * Theme metadata for versioning and compliance tracking.
 */
export interface ThemeMetadata {
  /** Measured contrast ratios for key color combinations */
  contrastRatios: ContrastRatios;
  /** Semantic version (e.g., "1.0.0") */
  version: string;
  /** WCAG conformance level */
  wcagLevel: WCAGLevel;
  /** Optional theme author/creator */
  author?: string;
  /** Optional categorization tags */
  tags?: string[];
}

// ============================================================================
// Theme Entity
// ============================================================================

/**
 * Complete theme definition with colors, metadata, and display information.
 * 
 * @remarks
 * Theme objects are immutable at runtime. To create a new theme, use the
 * `createTheme()` factory function with validation.
 * 
 * @example
 * ```typescript
 * const myTheme: Theme = {
 *   id: 'dark',
 *   name: 'Dark Theme',
 *   description: 'Low-light optimized theme',
 *   colors: { ... },
 *   metadata: { ... }
 * };
 * ```
 */
export interface Theme {
  /** Unique theme identifier */
  id: ThemeId;
  /** Display name shown in UI */
  name: string;
  /** User-facing description (tooltip/help text) */
  description: string;
  /** Complete color palette */
  colors: ThemeColors;
  /** Accessibility and version metadata */
  metadata: ThemeMetadata;
}

// ============================================================================
// User Preference
// ============================================================================

/**
 * User's saved theme preference (persisted in localStorage).
 * 
 * @remarks
 * This is the only entity that is serialized to localStorage.
 * Keep this structure minimal to reduce storage footprint.
 */
export interface ThemePreference {
  /** Selected theme ID */
  themeId: ThemeId;
  /** Last update timestamp (ISO 8601 format) */
  updatedAt: string;
}

// ============================================================================
// Global Configuration
// ============================================================================

/**
 * Global theme system configuration (singleton).
 * 
 * @remarks
 * This is the central registry of all available themes and system settings.
 * Modify this to add new themes or change system behavior.
 */
export interface ThemeConfig {
  /** All available themes */
  themes: Theme[];
  /** Fallback theme ID when no preference is saved or preference is invalid */
  defaultTheme: ThemeId;
  /** localStorage key for persisting preference */
  storageKey: string;
  /** Feature flag: enable user-created custom themes (future) */
  allowCustomThemes: boolean;
}

// ============================================================================
// Validation Types
// ============================================================================

/**
 * Result of theme validation.
 */
export interface ValidationResult {
  /** Whether validation passed */
  valid: boolean;
  /** List of validation errors (empty if valid) */
  errors: string[];
  /** Optional warnings (non-blocking) */
  warnings?: string[];
}

/**
 * Contrast validation parameters.
 */
export interface ContrastCheck {
  /** Foreground color (text, icon) */
  foreground: string;
  /** Background color */
  background: string;
  /** Minimum required contrast ratio */
  minRatio: number;
  /** Text size category */
  textSize: 'normal' | 'large';
}

// ============================================================================
// Type Guards
// ============================================================================

/**
 * Type guard to check if a string is a valid ThemeId.
 * 
 * @param value - Value to check
 * @returns True if value is a valid ThemeId
 * 
 * @example
 * ```typescript
 * if (isValidThemeId(userInput)) {
 *   setTheme(userInput); // TypeScript knows this is ThemeId
 * }
 * ```
 */
export function isValidThemeId(value: unknown): value is ThemeId {
  return typeof value === 'string' && 
         ['light', 'dark', 'high-contrast'].includes(value);
}

/**
 * Type guard to check if an object is a valid ThemePreference.
 * 
 * @param value - Value to check
 * @returns True if value is a valid ThemePreference
 * 
 * @example
 * ```typescript
 * const stored = JSON.parse(localStorage.getItem('theme'));
 * if (isValidThemePreference(stored)) {
 *   applyTheme(stored.themeId);
 * }
 * ```
 */
export function isValidThemePreference(value: unknown): value is ThemePreference {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  
  const pref = value as Record<string, unknown>;
  
  return (
    isValidThemeId(pref.themeId) &&
    typeof pref.updatedAt === 'string' &&
    !isNaN(Date.parse(pref.updatedAt))
  );
}

/**
 * Type guard to check if a string is a valid CSS color.
 * 
 * @param value - Value to check
 * @returns True if value is a valid CSS color format
 * 
 * @example
 * ```typescript
 * if (isValidColor('#ff0000')) {
 *   // Safe to use as a color value
 * }
 * ```
 */
export function isValidColor(value: unknown): value is string {
  if (typeof value !== 'string') {
    return false;
  }
  
  // Hex: #rgb, #rrggbb, #rrggbbaa
  const hexPattern = /^#([0-9A-Fa-f]{3}){1,2}([0-9A-Fa-f]{2})?$/;
  // RGB/RGBA: rgb(r, g, b) or rgba(r, g, b, a)
  const rgbPattern = /^rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(,\s*[\d.]+\s*)?\)$/;
  // HSL/HSLA: hsl(h, s%, l%) or hsla(h, s%, l%, a)
  const hslPattern = /^hsla?\(\s*\d+\s*,\s*\d+%\s*,\s*\d+%\s*(,\s*[\d.]+\s*)?\)$/;
  
  return hexPattern.test(value) || rgbPattern.test(value) || hslPattern.test(value);
}

// ============================================================================
// Utility Types
// ============================================================================

/**
 * Extract color keys from ThemeColors interface.
 * Useful for iterating over all color properties.
 */
export type ColorKey = keyof ThemeColors;

/**
 * Readonly version of Theme for immutable theme definitions.
 */
export type ReadonlyTheme = Readonly<Theme> & {
  readonly colors: Readonly<ThemeColors>;
  readonly metadata: Readonly<ThemeMetadata>;
};

/**
 * Partial theme for updates/patches (advanced use cases).
 */
export type ThemeUpdate = Partial<Omit<Theme, 'id'>> & Pick<Theme, 'id'>;

// ============================================================================
// Constants
// ============================================================================

/**
 * Default localStorage key for theme preference.
 */
export const DEFAULT_STORAGE_KEY = 'app-theme-preference' as const;

/**
 * Default theme ID (fallback when no preference exists).
 */
export const DEFAULT_THEME_ID: ThemeId = 'light';

/**
 * Minimum contrast ratios per WCAG standards.
 */
export const WCAG_CONTRAST_MINIMUMS = {
  AA: {
    normalText: 4.5,
    largeText: 3.0,
    uiComponents: 3.0,
  },
  AAA: {
    normalText: 7.0,
    largeText: 4.5,
    uiComponents: 4.5,
  },
} as const;

// ============================================================================
// Factory Functions
// ============================================================================

/**
 * Creates a new ThemePreference with current timestamp.
 * 
 * @param themeId - Theme ID to save
 * @returns ThemePreference object
 * 
 * @example
 * ```typescript
 * const preference = createThemePreference('dark');
 * localStorage.setItem('theme', JSON.stringify(preference));
 * ```
 */
export function createThemePreference(themeId: ThemeId): ThemePreference {
  return {
    themeId,
    updatedAt: new Date().toISOString(),
  };
}

/**
 * Creates a ValidationResult from validation checks.
 * 
 * @param errors - Array of error messages
 * @param warnings - Optional array of warning messages
 * @returns ValidationResult object
 */
export function createValidationResult(
  errors: string[],
  warnings?: string[]
): ValidationResult {
  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}

// ============================================================================
// Default Export
// ============================================================================

/**
 * Default export: Namespace containing all utilities.
 */
export default {
  // Type guards
  isValidThemeId,
  isValidThemePreference,
  isValidColor,
  
  // Factory functions
  createThemePreference,
  createValidationResult,
  
  // Constants
  DEFAULT_STORAGE_KEY,
  DEFAULT_THEME_ID,
  WCAG_CONTRAST_MINIMUMS,
};
