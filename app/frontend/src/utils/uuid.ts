// UUID generation utilities

/**
 * Generate a UUID v4
 * Uses crypto.randomUUID() when available (secure contexts), falls back to fallback implementation
 */
export function generateUUID(): string {
  // Use crypto.randomUUID() if available (HTTPS/secure contexts)
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  
  // Fallback for non-secure contexts
  return fallbackUUID();
}

/**
 * Fallback UUID v4 generation for non-secure contexts
 * Based on RFC4122 standard
 */
function fallbackUUID(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}
