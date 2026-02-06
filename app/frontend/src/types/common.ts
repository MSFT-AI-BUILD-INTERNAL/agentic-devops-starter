// Common type definitions shared across modules

/**
 * Validation result for entity validation
 */
export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

/**
 * Create a successful validation result
 */
export function validResult(): ValidationResult {
  return { valid: true, errors: [] };
}

/**
 * Create a failed validation result with errors
 */
export function invalidResult(errors: string[]): ValidationResult {
  return { valid: false, errors };
}
