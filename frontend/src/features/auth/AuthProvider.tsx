import { createContext, useContext, useState, type ReactNode } from 'react'
import { clearSession, loadSession, saveSession, type SessionUser } from './session'

type AuthContextValue = {
  user: SessionUser | null
  signIn: (user: SessionUser) => void
  signOut: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(loadSession)

  const signIn = (next: SessionUser) => {
    saveSession(next)
    setUser(next)
  }

  const signOut = () => {
    clearSession()
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, signIn, signOut }}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react/only-export-components
export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>')
  return context
}
