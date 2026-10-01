import { useTheme } from '../theme/ThemeProvider'
import type { ThemePreference } from '../theme/theme'
import './ThemeToggle.css'

const options: { value: ThemePreference; label: string; icon: string }[] = [
  { value: 'light', label: 'Light', icon: '☀' },
  { value: 'system', label: 'System', icon: '◐' },
  { value: 'dark', label: 'Dark', icon: '☾' },
]

export function ThemeToggle() {
  const { preference, setPreference } = useTheme()

  return (
    <div className="theme-toggle glass" role="radiogroup" aria-label="Color theme">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={preference === option.value}
          className="theme-toggle__option"
          onClick={() => setPreference(option.value)}
          title={option.label}
        >
          <span aria-hidden="true">{option.icon}</span>
          <span className="theme-toggle__label">{option.label}</span>
        </button>
      ))}
    </div>
  )
}
