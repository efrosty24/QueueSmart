import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import {
  applyTheme,
  getStoredPreference,
  onSystemThemeChange,
  resolveTheme,
  storePreference,
  type ResolvedTheme,
  type ThemePreference,
} from './theme'

type ThemeContextValue = {
  preference: ThemePreference
  resolvedTheme: ResolvedTheme
  setPreference: (preference: ThemePreference) => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [preference, setPreferenceState] = useState<ThemePreference>(getStoredPreference)
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>(() => resolveTheme(preference))

  useEffect(() => {
    const update = () => {
      const next = resolveTheme(preference)
      setResolvedTheme(next)
      applyTheme(next)
    }
    update()
    // Only "system" needs to react to OS changes.
    if (preference === 'system') return onSystemThemeChange(update)
  }, [preference])

  const setPreference = (next: ThemePreference) => {
    storePreference(next)
    setPreferenceState(next)
  }

  return (
    <ThemeContext.Provider value={{ preference, resolvedTheme, setPreference }}>
      {children}
    </ThemeContext.Provider>
  )
}

// eslint-disable-next-line react/only-export-components
export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) throw new Error('useTheme must be used inside <ThemeProvider>')
  return context
}
