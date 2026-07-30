// In dev, Vite proxies /api to the FastAPI backend (see vite.config.ts).
// In prod, set VITE_API_BASE_URL to the deployed API origin.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'

// Phase 2 has no session sidebar yet, so the single active session id is
// persisted here instead. Revisit once session switching UI exists.
export const ACTIVE_SESSION_STORAGE_KEY = 'lenny.activeSessionId'
