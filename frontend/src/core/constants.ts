// In dev, Vite proxies /api to the FastAPI backend (see vite.config.ts).
// In prod, set VITE_API_BASE_URL to the deployed API origin.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'
