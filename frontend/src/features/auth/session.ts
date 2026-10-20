// The signed-in session, saved in the browser so it survives reloads. The token
// comes from the backend and lasts 7 days. The saved role is only a cache for the
// first paint: AuthProvider re-checks it with GET /api/auth/me on every load.

export type Role = 'patient' | 'admin'

export type SessionUser = {
  id: string
  email: string
  role: Role
}

export type StoredSession = {
  token: string
  // ISO 8601 timestamp from the server.
  expiresAt: string
  user: SessionUser
}

const SESSION_STORAGE_KEY = 'queuesmart-session'

export function loadStoredSession(): StoredSession | null {
  try {
    const raw = localStorage.getItem(SESSION_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<StoredSession>
    if (typeof parsed.token !== 'string' || typeof parsed.expiresAt !== 'string' || !parsed.user) {
      clearSession()
      return null
    }
    // Drop expired sessions without asking the server.
    if (Date.parse(parsed.expiresAt) <= Date.now()) {
      clearSession()
      return null
    }
    return parsed as StoredSession
  } catch {
    return null
  }
}

// The signed-in user, for code outside React (e.g. history lookups).
export function loadSession(): SessionUser | null {
  return loadStoredSession()?.user ?? null
}

export function saveSession(session: StoredSession) {
  try {
    localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session))
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
