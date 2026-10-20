import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { ApiError } from '../../lib/api'
import { fetchCurrentUser, logout } from './authApi'
import { clearSession, loadStoredSession, saveSession, type SessionUser, type StoredSession } from './session'

type AuthContextValue = {
  user: SessionUser | null
  token: string | null
  // True while a saved session is being confirmed with the server on page load.
  checking: boolean
  signIn: (session: StoredSession) => void
  signOut: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<StoredSession | null>(loadStoredSession)
  const [checking, setChecking] = useState(() => session !== null)

  // Confirm a saved session once per load. The server's answer replaces the cached
  // email and role, so an edited localStorage entry can't grant admin access.
  useEffect(() => {
    const stored = loadStoredSession()
    if (!stored) return
    let cancelled = false
    fetchCurrentUser(stored.token)
      .then((user) => {
        if (cancelled) return
        const confirmed = { ...stored, user }
        saveSession(confirmed)
        setSession(confirmed)
      })
      .catch((error: unknown) => {
        if (cancelled) return
        // Expired or revoked: sign out. Network errors keep the cached session.
        if (error instanceof ApiError && error.status === 401) {
          clearSession()
          setSession(null)
        }
      })
      .finally(() => {
        if (!cancelled) setChecking(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const signIn = (next: StoredSession) => {
    saveSession(next)
    setSession(next)
    setChecking(false)
  }

  const signOut = () => {
    const token = session?.token
    clearSession()
    setSession(null)
    // Revoke on the server too; the user is signed out locally either way.
    if (token) logout(token).catch(() => {})
  }

  return (
    <AuthContext.Provider value={{ user: session?.user ?? null, token: session?.token ?? null, checking, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

// eslint-disable-next-line react/only-export-components
export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>')
  return context
}
