import { generateUUID } from './uuid';

const ISOLATION_SESSION_STORAGE_KEY = 'copilot-isolation-session-id';

export function getIsolationSessionId(): string {
  const existing = window.localStorage.getItem(ISOLATION_SESSION_STORAGE_KEY);
  if (existing && existing.trim().length > 0) {
    return existing;
  }

  const created = generateUUID();
  window.localStorage.setItem(ISOLATION_SESSION_STORAGE_KEY, created);
  return created;
}
