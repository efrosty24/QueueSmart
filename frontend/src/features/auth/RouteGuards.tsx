import { Navigate, Outlet, useLocation } from 'react-router'
import { useAuth } from './AuthProvider'

// Wraps pages that need a signed-in user. Sends everyone else to /login.
export function RequireAuth() {
  const { user, checking } = useAuth()
  const location = useLocation()
  // Wait for the server to confirm a saved session before deciding.
  if (checking) return null
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return <Outlet />
}

// Wraps /login and /register. Signed-in users go straight to their dashboard.
export function RedirectIfSignedIn() {
  const { user, checking } = useAuth()
  if (checking) return null
  if (user) return <Navigate to={user.role === 'admin' ? '/admin' : '/dashboard'} replace />
  return <Outlet />
}

// Wraps pages that need a signed-in admin. Sends patients to /dashboard and signed-out users to /login.
export function RequireAdmin() {
  const { user, checking } = useAuth()
  const location = useLocation()
  // The role checked here comes from the server (login response or GET /api/auth/me).
  if (checking) return null
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (user.role !== 'admin') return <Navigate to="/dashboard" replace />
  return <Outlet />
}
