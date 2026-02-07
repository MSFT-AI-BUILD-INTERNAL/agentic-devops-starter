// API configuration utilities

/**
 * Get the base URL for the AGUI API endpoint
 * Falls back to '/api' for production (reverse proxy)
 */
export function getApiBaseUrl(): string {
  return import.meta.env.VITE_AGUI_ENDPOINT || '/api';
}

/**
 * Build a full API URL with optional query parameters
 */
export function buildApiUrl(path: string, params?: Record<string, string>): string {
  const baseUrl = getApiBaseUrl();
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  
  // Build URL using URL API for consistency
  const url = new URL(cleanPath, baseUrl.startsWith('http') ? baseUrl : `http://placeholder${baseUrl}`);
  
  // Add query parameters if provided
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.set(key, value);
    });
  }
  
  // Return relative URL if baseUrl was relative, otherwise return absolute
  if (!baseUrl.startsWith('http')) {
    return url.pathname + url.search;
  }
  
  return url.toString();
}
