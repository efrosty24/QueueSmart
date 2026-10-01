import { useEffect, useRef, useState } from 'react'
import { LuHistory, LuLayoutDashboard, LuListOrdered, LuLogOut, LuMenu, LuPlus, LuX } from 'react-icons/lu'
import { NavLink, Outlet, useNavigate } from 'react-router'
import { useAuth } from '../features/auth/AuthProvider'
import { ConfirmDialog } from './ConfirmDialog'
import { ThemeToggle } from './ThemeToggle'
// Brand styles (.app-brand) are shared with the signed-out header.
import './AppHeader.css'
import './AppShell.css'

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LuLayoutDashboard },
  { to: '/join-queue', label: 'Join queue', icon: LuPlus },
  { to: '/queue', label: 'Queue status', icon: LuListOrdered },
  { to: '/history', label: 'History', icon: LuHistory },
]

// Layout for every signed-in page: sidebar on the left, page content on the right.
// Below 900px the sidebar becomes a slide-in drawer opened from the top bar.
export function AppShell() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const [navOpen, setNavOpen] = useState(false)
  const [confirmSignOut, setConfirmSignOut] = useState(false)
  const closeButtonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!navOpen) return
    closeButtonRef.current?.focus()
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setNavOpen(false)
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [navOpen])

  const handleSignOut = () => {
    setConfirmSignOut(false)
    signOut()
    navigate('/login', { replace: true })
  }

  return (
    <div className="app-shell">
      <header className="app-shell__topbar glass">
        <button
          type="button"
          className="icon-button"
          onClick={() => setNavOpen(true)}
          aria-label="Open menu"
          aria-expanded={navOpen}
          aria-controls="app-sidebar"
        >
          <LuMenu aria-hidden="true" />
        </button>
        <Brand />
      </header>

      <aside id="app-sidebar" className={`sidebar glass${navOpen ? ' is-open' : ''}`} aria-label="Main">
        <div className="sidebar__top">
          <Brand />
          <button
            ref={closeButtonRef}
            type="button"
            className="icon-button sidebar__close"
            onClick={() => setNavOpen(false)}
            aria-label="Close menu"
          >
            <LuX aria-hidden="true" />
          </button>
        </div>

        <nav className="sidebar__nav">
          <ul>
            {navItems.map(({ to, label, icon: Icon }) => (
              <li key={to}>
                <NavLink to={to} className="sidebar__link" onClick={() => setNavOpen(false)}>
                  <Icon aria-hidden="true" className="sidebar__link-icon" />
                  {label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <div className="sidebar__footer">
          <ThemeToggle />
          {user && (
            <p className="sidebar__user" title={user.email}>
              <span className="sidebar__user-label">Signed in as</span>
              <span className="sidebar__user-email">{user.email}</span>
            </p>
          )}
          <button
            type="button"
            className="btn btn-pill btn-danger-hover sidebar__signout"
            onClick={() => setConfirmSignOut(true)}
          >
            <LuLogOut aria-hidden="true" />
            Sign out
          </button>
        </div>
      </aside>

      {navOpen && <div className="app-shell__backdrop" onClick={() => setNavOpen(false)} aria-hidden="true" />}

      <main className="app-shell__main">
        <Outlet />
      </main>

      <ConfirmDialog
        open={confirmSignOut}
        tone="danger"
        icon={<LuLogOut aria-hidden="true" />}
        title="Sign out?"
        message="You'll need to sign in again to check your place in line."
        confirmLabel="Sign out"
        onConfirm={handleSignOut}
        onCancel={() => setConfirmSignOut(false)}
      />
    </div>
  )
}

function Brand() {
  return (
    <span className="app-brand">
      <span className="app-brand__mark" aria-hidden="true">
        Q
      </span>
      QueueSmart
    </span>
  )
}
