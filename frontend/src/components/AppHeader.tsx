import type { ReactNode } from 'react'
import { ThemeToggle } from './ThemeToggle'
import './AppHeader.css'

// Top bar shared by every page: brand on the left, theme switch plus any extra actions on the right.
export function AppHeader({ actions }: { actions?: ReactNode }) {
  return (
    <header className="app-header">
      <span className="app-brand">
        <span className="app-brand__mark" aria-hidden="true">
          Q
        </span>
        QueueSmart
      </span>
      <div className="app-header__actions">
        <ThemeToggle />
        {actions}
      </div>
    </header>
  )
}
