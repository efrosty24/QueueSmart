import { Navigate, Outlet, useLocation } from 'react-router'
import { useAuth } from './AuthProvider'

// Wraps pages that need a signed-in user. Sends everyone else to /login.
export function RequireAuth() {
  const { user } = useAuth()
  const location = useLocation()
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return <Outlet />
}

// Wraps /login and /register. Signed-in users go straight to the dashboard.
export function RedirectIfSignedIn() {
  const { user } = useAuth()
  if (user) return <Navigate to="/dashboard" replace />
  return <Outlet />
}
