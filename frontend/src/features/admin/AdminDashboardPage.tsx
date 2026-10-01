import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { AppHeader } from '../../components/AppHeader'
import { useAuth } from '../auth/AuthProvider'
import { fetchServices, setQueueStatus, type Service } from './adminApi'
import './admin.css'

// Admin landing page: every service's queue at a glance, with a quick open/close action.
export function AdminDashboardPage() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const [services, setServices] = useState<Service[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pendingIds, setPendingIds] = useState<Set<string>>(new Set())

  useEffect(() => {
    let cancelled = false
    fetchServices()
      .then((data) => {
        if (!cancelled) setServices(data)
      })
      .catch(() => {
        if (!cancelled) setError('Could not load services. Try refreshing the page.')
      })
    return () => {
      cancelled = true
    }
  }, [])

  const handleToggle = async (service: Service) => {
    const nextStatus = service.status === 'open' ? 'closed' : 'open'
    setPendingIds((ids) => new Set(ids).add(service.id))
    setError(null)
    try {
      const updated = await setQueueStatus(service.id, nextStatus)
      setServices((current) => current?.map((item) => (item.id === updated.id ? updated : item)) ?? current)
    } catch {
      setError(`Could not update ${service.name}. Try again.`)
    } finally {
      setPendingIds((ids) => {
        const next = new Set(ids)
        next.delete(service.id)
        return next
      })
    }
  }

  const handleSignOut = () => {
    signOut()
    navigate('/login', { replace: true })
  }

  // RequireAdmin guarantees a signed-in admin.
  if (!user) return null

  return (
    <div className="admin-page">
      <AppHeader
        actions={
          <>
            <Link to="/admin/services" className="btn btn-ghost">
              Manage services
            </Link>
            <button type="button" className="btn btn-ghost" onClick={handleSignOut}>
              Sign out
            </button>
          </>
        }
      />

      <main className="admin-page__main">
        <section className="admin-intro glass" aria-labelledby="admin-title">
          <p className="admin-intro__eyebrow">Admin dashboard</p>
          <h1 id="admin-title">Queue overview</h1>
          <p className="admin-intro__note">Open or close a queue to control whether patients can join it.</p>
        </section>

        {error && (
          <div className="alert alert-error" role="alert">
            {error}
          </div>
        )}

        <section className="service-list" aria-label="Services">
          {services === null && !error && <p className="service-list__loading">Loading services…</p>}
          {services?.map((service) => {
            const isPending = pendingIds.has(service.id)
            const isOpen = service.status === 'open'
            return (
              <article key={service.id} className="service-card glass">
                <div className="service-card__info">
                  <h2 className="service-card__name">{service.name}</h2>
                  <span className={`status-badge status-badge--${service.status}`}>
                    {isOpen ? 'Open' : 'Closed'}
                  </span>
                </div>
                <p className="service-card__queue">
                  <span className="service-card__queue-count">{service.queueLength}</span>
                  {service.queueLength === 1 ? 'person waiting' : 'people waiting'}
                </p>
                <button
                  type="button"
                  className={`btn ${isOpen ? 'btn-ghost' : 'btn-primary'} btn-block`}
                  onClick={() => handleToggle(service)}
                  disabled={isPending}
                >
                  {isPending ? 'Updating…' : isOpen ? 'Close queue' : 'Open queue'}
                </button>
              </article>
            )
          })}
        </section>
      </main>
    </div>
  )
}
