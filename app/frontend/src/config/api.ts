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
  let url: string;

  if (baseUrl.startsWith('http://') || baseUrl.startsWith('https://')) {
    // Absolute URL
    const urlObj = new URL(path, baseUrl);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        urlObj.searchParams.set(key, value);
      });
    }
    url = urlObj.toString();
  } else {
    // Relative URL
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    const fullPath = `${baseUrl}${cleanPath}`;
    if (params) {
      const queryString = new URLSearchParams(params).toString();
      url = queryString ? `${fullPath}?${queryString}` : fullPath;
    } else {
      url = fullPath;
    }
  }

  return url;
}
