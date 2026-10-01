import type { IconType } from 'react-icons'
import { LuMonitor, LuMoon, LuSun } from 'react-icons/lu'
import { useTheme } from '../theme/ThemeProvider'
import type { ThemePreference } from '../theme/theme'
import './ThemeToggle.css'

const options: { value: ThemePreference; label: string; icon: IconType }[] = [
  { value: 'light', label: 'Light', icon: LuSun },
  { value: 'system', label: 'System', icon: LuMonitor },
  { value: 'dark', label: 'Dark', icon: LuMoon },
]

export function ThemeToggle() {
  const { preference, setPreference } = useTheme()

  return (
    <div className="theme-toggle glass" role="radiogroup" aria-label="Color theme">
      {options.map(({ value, label, icon: Icon }) => (
        <button
          key={value}
          type="button"
          role="radio"
          aria-checked={preference === value}
          className="theme-toggle__option"
          onClick={() => setPreference(value)}
          title={label}
        >
          <Icon aria-hidden="true" />
          <span className="theme-toggle__label">{label}</span>
        </button>
      ))}
    </div>
  )
}
