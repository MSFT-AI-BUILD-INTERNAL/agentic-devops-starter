/**
 * Theme Utility Functions
 * 
 * This file contains utility functions for theme validation, contrast checking,
 * and color format validation.
 */

import type { Theme, ValidationResult, ContrastCheck } from '../types/theme';
import { isValidColor, WCAG_CONTRAST_MINIMUMS, createValidationResult } from '../types/theme';

// ============================================================================
// Color Utilities
// ============================================================================

/**
 * Convert hex color to RGB values.
 * 
 * @param hex - Hex color string (e.g., "#ff0000" or "#f00")
 * @returns RGB object { r, g, b } with values 0-255
 */
export function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  // Remove # if present
  const cleanHex = hex.replace(/^#/, '');
  
  // Handle 3-digit hex
  if (cleanHex.length === 3) {
    const r = parseInt(cleanHex[0] + cleanHex[0], 16);
    const g = parseInt(cleanHex[1] + cleanHex[1], 16);
    const b = parseInt(cleanHex[2] + cleanHex[2], 16);
    return { r, g, b };
  }
  
  // Handle 6-digit hex
  if (cleanHex.length === 6) {
    const r = parseInt(cleanHex.substring(0, 2), 16);
    const g = parseInt(cleanHex.substring(2, 4), 16);
    const b = parseInt(cleanHex.substring(4, 6), 16);
    return { r, g, b };
  }
  
  return null;
}

/**
 * Calculate relative luminance of a color (WCAG formula).
 * 
 * @param rgb - RGB color object { r, g, b } with values 0-255
 * @returns Relative luminance (0-1)
 */
export function getRelativeLuminance(rgb: { r: number; g: number; b: number }): number {
  // Convert RGB values to 0-1 range and apply WCAG formula
  const rNorm = rgb.r / 255;
  const gNorm = rgb.g / 255;
  const bNorm = rgb.b / 255;
  
  const r = rNorm <= 0.03928 ? rNorm / 12.92 : Math.pow((rNorm + 0.055) / 1.055, 2.4);
  const g = gNorm <= 0.03928 ? gNorm / 12.92 : Math.pow((gNorm + 0.055) / 1.055, 2.4);
  const b = bNorm <= 0.03928 ? bNorm / 12.92 : Math.pow((bNorm + 0.055) / 1.055, 2.4);
  
  // Calculate luminance using WCAG formula
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/**
 * Calculate contrast ratio between two colors (WCAG formula).
 * 
 * @param color1 - First color (hex string)
 * @param color2 - Second color (hex string)
 * @returns Contrast ratio (1-21) or 0 if invalid colors
 */
export function calculateContrastRatio(color1: string, color2: string): number {
  const rgb1 = hexToRgb(color1);
  const rgb2 = hexToRgb(color2);
  
  if (!rgb1 || !rgb2) {
    return 0;
  }
  
  const lum1 = getRelativeLuminance(rgb1);
  const lum2 = getRelativeLuminance(rgb2);
  
  const lighter = Math.max(lum1, lum2);
  const darker = Math.min(lum1, lum2);
  
  return (lighter + 0.05) / (darker + 0.05);
}

// ============================================================================
// Contrast Validation
// ============================================================================

/**
 * Validate contrast ratio between foreground and background colors.
 * 
 * @param check - Contrast check parameters
 * @returns Result with pass/fail and actual ratio
 */
export function validateContrast(check: ContrastCheck): { pass: boolean; ratio: number } {
  const ratio = calculateContrastRatio(check.foreground, check.background);
  const minRequired = check.textSize === 'normal' 
    ? WCAG_CONTRAST_MINIMUMS.AA.normalText 
    : WCAG_CONTRAST_MINIMUMS.AA.largeText;
  
  return {
    pass: ratio >= minRequired,
    ratio: parseFloat(ratio.toFixed(2)),
  };
}

/**
 * Validate all contrast ratios for a theme.
 * 
 * @param theme - Theme to validate
 * @returns Validation result with errors for failed checks
 */
export function validateThemeContrast(theme: Theme): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];
  
  // Define contrast checks for key color combinations
  const contrastChecks: Array<{ check: ContrastCheck; description: string }> = [
    {
      check: {
        foreground: theme.colors.textPrimary,
        background: theme.colors.bgPrimary,
        minRatio: WCAG_CONTRAST_MINIMUMS.AA.normalText,
        textSize: 'normal',
      },
      description: 'Primary text on primary background',
    },
    {
      check: {
        foreground: theme.colors.textSecondary,
        background: theme.colors.bgPrimary,
        minRatio: WCAG_CONTRAST_MINIMUMS.AA.normalText,
        textSize: 'normal',
      },
      description: 'Secondary text on primary background',
    },
    {
      check: {
        foreground: theme.colors.messageBubbleUserText,
        background: theme.colors.messageBubbleUser,
        minRatio: WCAG_CONTRAST_MINIMUMS.AA.normalText,
        textSize: 'normal',
      },
      description: 'User message text on user message background',
    },
    {
      check: {
        foreground: theme.colors.messageBubbleAssistantText,
        background: theme.colors.messageBubbleAssistant,
        minRatio: WCAG_CONTRAST_MINIMUMS.AA.normalText,
        textSize: 'normal',
      },
      description: 'Assistant message text on assistant message background',
    },
    {
      check: {
        foreground: theme.colors.messageBubbleToolText,
        background: theme.colors.messageBubbleTool,
        minRatio: WCAG_CONTRAST_MINIMUMS.AA.normalText,
        textSize: 'normal',
      },
      description: 'Tool message text on tool message background',
    },
    {
      check: {
        foreground: theme.colors.border,
        background: theme.colors.bgPrimary,
        minRatio: WCAG_CONTRAST_MINIMUMS.AA.uiComponents,
        textSize: 'large',
      },
      description: 'Border on primary background',
    },
  ];
  
  // Validate each contrast check
  contrastChecks.forEach(({ check, description }) => {
    const result = validateContrast(check);
    if (!result.pass) {
      errors.push(
        `${description}: Contrast ratio ${result.ratio}:1 is below minimum ${check.minRatio}:1 (WCAG AA)`
      );
    } else if (result.ratio < WCAG_CONTRAST_MINIMUMS.AAA.normalText && check.textSize === 'normal') {
      warnings.push(
        `${description}: Contrast ratio ${result.ratio}:1 meets WCAG AA but not AAA (7.0:1 recommended)`
      );
    }
  });
  
  return createValidationResult(errors, warnings);
}

// ============================================================================
// Color Format Validation
// ============================================================================

/**
 * Validate all color formats in a theme.
 * 
 * @param theme - Theme to validate
 * @returns Validation result with errors for invalid colors
 */
export function validateThemeColors(theme: Theme): ValidationResult {
  const errors: string[] = [];
  
  // Check all color properties
  Object.entries(theme.colors).forEach(([key, color]) => {
    if (!isValidColor(color)) {
      errors.push(`Invalid color format for ${key}: ${color}`);
    }
  });
  
  return createValidationResult(errors);
}

// ============================================================================
// Theme Validation
// ============================================================================

/**
 * Perform complete validation of a theme.
 * Checks color formats, contrast ratios, and metadata.
 * 
 * @param theme - Theme to validate
 * @returns Validation result with all errors and warnings
 */
export function validateTheme(theme: Theme): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];
  
  // Validate color formats
  const colorValidation = validateThemeColors(theme);
  errors.push(...colorValidation.errors);
  
  // Validate contrast ratios
  const contrastValidation = validateThemeContrast(theme);
  errors.push(...contrastValidation.errors);
  if (contrastValidation.warnings) {
    warnings.push(...contrastValidation.warnings);
  }
  
  // Validate metadata
  if (!theme.metadata.version.match(/^\d+\.\d+\.\d+$/)) {
    errors.push(`Invalid version format: ${theme.metadata.version} (must be semantic version)`);
  }
  
  if (theme.metadata.contrastRatios.normalText < WCAG_CONTRAST_MINIMUMS.AA.normalText) {
    errors.push(
      `Normal text contrast ratio ${theme.metadata.contrastRatios.normalText}:1 ` +
      `is below WCAG AA minimum ${WCAG_CONTRAST_MINIMUMS.AA.normalText}:1`
    );
  }
  
  if (theme.metadata.contrastRatios.largeText < WCAG_CONTRAST_MINIMUMS.AA.largeText) {
    errors.push(
      `Large text contrast ratio ${theme.metadata.contrastRatios.largeText}:1 ` +
      `is below WCAG AA minimum ${WCAG_CONTRAST_MINIMUMS.AA.largeText}:1`
    );
  }
  
  return createValidationResult(errors, warnings);
}

// ============================================================================
// Theme Persistence Utilities
// ============================================================================

/**
 * Safely parse theme preference from localStorage.
 * 
 * @param stored - Raw value from localStorage
 * @returns Parsed theme preference or null if invalid
 */
export function parseThemePreference(stored: string | null): { themeId: string; updatedAt: string } | null {
  if (!stored) {
    return null;
  }
  
  try {
    const parsed = JSON.parse(stored);
    if (typeof parsed.themeId === 'string' && typeof parsed.updatedAt === 'string') {
      return parsed;
    }
  } catch (error) {
    console.warn('Failed to parse theme preference from localStorage:', error);
  }
  
  return null;
}

/**
 * Apply theme to document by setting data-theme attribute.
 * 
 * @param themeId - Theme ID to apply
 */
export function applyThemeToDocument(themeId: string): void {
  // Add temporary class to disable transitions
  document.documentElement.classList.add('theme-changing');
  
  // Set the theme attribute
  document.documentElement.setAttribute('data-theme', themeId);
  
  // Remove temporary class after a short delay
  setTimeout(() => {
    document.documentElement.classList.remove('theme-changing');
  }, 50);
}
