// In dev, Vite proxies /api to the FastAPI backend (see vite.config.ts).
// In prod, set VITE_API_BASE_URL to the deployed API origin.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'

// Persists which session is active across reloads. The session list itself
// always comes from the backend (GET /sessions) via
// features/sessions/hooks/useSessions.ts — this key only remembers the
// selection.
export const ACTIVE_SESSION_STORAGE_KEY = 'lenny.activeSessionId'
