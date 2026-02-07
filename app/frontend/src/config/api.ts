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
  
  // Handle absolute URLs
  if (baseUrl.startsWith('http://') || baseUrl.startsWith('https://')) {
    const url = new URL(cleanPath, baseUrl);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        url.searchParams.set(key, value);
      });
    }
    return url.toString();
  }
  
  // Handle relative URLs
  const fullPath = `${baseUrl}${cleanPath}`;
  if (params) {
    const queryString = new URLSearchParams(params).toString();
    return queryString ? `${fullPath}?${queryString}` : fullPath;
  }
  
  return fullPath;
}
