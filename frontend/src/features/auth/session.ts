// Mock session stored in the browser. There is no backend yet, so "signed in"
// just means this record exists. Never treat it as real authentication.
// TODO: replace with the token/session returned by the FastAPI backend.

export type Role = 'patient' | 'admin'

export type SessionUser = {
  email: string
  role: Role
}

const SESSION_STORAGE_KEY = 'queuesmart-session'

export function loadSession(): SessionUser | null {
  try {
    const raw = localStorage.getItem(SESSION_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<SessionUser>
    if (typeof parsed.email !== 'string') return null
    return { email: parsed.email, role: parsed.role === 'admin' ? 'admin' : 'patient' }
  } catch {
    return null
  }
}

export function saveSession(user: SessionUser) {
  try {
    localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(user))
  } catch {
    // Storage blocked; the session lasts until the page reloads.
  }
}

export function clearSession() {
  try {
    localStorage.removeItem(SESSION_STORAGE_KEY)
  } catch {
    // Nothing to clear.
  }
}
