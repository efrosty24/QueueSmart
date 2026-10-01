export type ThemePreference = 'light' | 'dark' | 'system'
export type ResolvedTheme = 'light' | 'dark'

// Keep in sync with the inline script in index.html, which applies the theme before React loads.
export const THEME_STORAGE_KEY = 'queuesmart-theme'

const darkQuery = '(prefers-color-scheme: dark)'

export function getStoredPreference(): ThemePreference {
  try {
    const value = localStorage.getItem(THEME_STORAGE_KEY)
    if (value === 'light' || value === 'dark' || value === 'system') return value
  } catch {
    // Storage can be blocked (private mode); fall back to system.
  }
  return 'system'
}

export function storePreference(preference: ThemePreference) {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, preference)
  } catch {
    // Ignore; the choice just won't persist.
  }
}

export function getSystemTheme(): ResolvedTheme {
  return window.matchMedia(darkQuery).matches ? 'dark' : 'light'
}

export function resolveTheme(preference: ThemePreference): ResolvedTheme {
  return preference === 'system' ? getSystemTheme() : preference
}

export function applyTheme(theme: ResolvedTheme) {
  document.documentElement.dataset.theme = theme
}

export function onSystemThemeChange(callback: () => void) {
  const query = window.matchMedia(darkQuery)
  query.addEventListener('change', callback)
  return () => query.removeEventListener('change', callback)
}
