import { useNavigate } from 'react-router'
import { AppHeader } from '../../components/AppHeader'
import { useAuth } from '../auth/AuthProvider'
import './dashboard.css'

// Placeholder landing page after sign-in. Queue, appointment and notification
// features will be added here in later assignments.
export function DashboardPage() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()

  const handleSignOut = () => {
    signOut()
    navigate('/login', { replace: true })
  }

  // RequireAuth guarantees a user; this keeps TypeScript happy.
  if (!user) return null

  return (
    <div className="dashboard-page">
      <AppHeader
        actions={
          <button type="button" className="btn btn-ghost" onClick={handleSignOut}>
            Sign out
          </button>
        }
      />

      <main className="dashboard-page__main">
        <section className="dashboard-welcome glass" aria-labelledby="dashboard-title">
          <p className="dashboard-welcome__eyebrow">Patient dashboard</p>
          <h1 id="dashboard-title">You're signed in</h1>
          <p className="dashboard-welcome__email">
            Signed in as <strong>{user.email}</strong>
          </p>
          <p className="dashboard-welcome__note">
            This is a preview. Joining the clinic queue, booking appointments and notifications are coming
            soon.
          </p>
        </section>
      </main>
    </div>
  )
}
