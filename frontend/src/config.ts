export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// The recruiter list itself requires a known recruiter, so the app needs one identity
// to start with. The switcher can change it afterwards.
export const DEFAULT_RECRUITER_ID: string = import.meta.env.VITE_DEFAULT_RECRUITER_ID ?? 'R-101'

export const PAGE_SIZE = 25
export const SEARCH_DELAY_MS = 300
