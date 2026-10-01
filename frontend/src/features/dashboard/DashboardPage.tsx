import { PageHeader } from '../../components/PageHeader'
import { useAuth } from '../auth/AuthProvider'
import './dashboard.css'

// Landing page after sign-in.
export function DashboardPage() {
  const { user } = useAuth()

  return (
    <>
      <PageHeader title="Dashboard" description={user ? `Welcome back, ${user.email}` : undefined} />
      <section className="dashboard-welcome glass" aria-labelledby="dashboard-welcome-title">
        <p className="dashboard-welcome__eyebrow">Patient dashboard</p>
        <h2 id="dashboard-welcome-title">You're signed in</h2>
        <p className="dashboard-welcome__note">Use the sidebar to check your queue status or past visits.</p>
      </section>
    </>
  )
}
