/**
 * Theme Utility Functions
 * 
 * Simple utility functions for theme management.
 */

/**
 * Apply theme to document by setting data-theme attribute.
 * 
 * @param themeId - Theme ID to apply
 */
export function applyThemeToDocument(themeId: string): void {
  // Add temporary class to disable transitions during theme change
  document.documentElement.classList.add('theme-changing');
  
  // Set the theme attribute
  document.documentElement.setAttribute('data-theme', themeId);
  
  // Remove temporary class after a short delay
  setTimeout(() => {
    document.documentElement.classList.remove('theme-changing');
  }, 50);
}

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
  } catch {
    console.warn('Failed to parse theme preference from localStorage');
  }
  
  return null;
}
