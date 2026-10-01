import { useEffect, useState, type ChangeEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { AppHeader } from '../../components/AppHeader'
import { SelectField } from '../../components/SelectField'
import { useAuth } from '../auth/AuthProvider'
import {
  fetchQueue,
  fetchServices,
  moveQueueEntry,
  removeQueueEntry,
  serveNextQueueEntry,
  type QueueEntry,
  type Service,
} from './adminApi'
import './admin.css'

// Lets admins view one service's queue at a time, reorder or remove people in
// it, and call the next person in — all simulated, no real notifications sent.
export function QueueManagementPage() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const { serviceId } = useParams<{ serviceId?: string }>()
  const [services, setServices] = useState<Service[] | null>(null)
  const [queue, setQueue] = useState<QueueEntry[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  // Load the service list once; land on the first service if the URL didn't name one.
  useEffect(() => {
    let cancelled = false
    fetchServices()
      .then((data) => {
        if (cancelled) return
        setServices(data)
        if (!serviceId && data.length > 0) navigate(`/admin/queue/${data[0].id}`, { replace: true })
      })
      .catch(() => {
        if (!cancelled) setError('Could not load services. Try refreshing the page.')
      })
    return () => {
      cancelled = true
    }
    // Intentionally runs once: this only needs serviceId as it was at mount, to redirect
    // when the URL has none yet.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Load the selected service's queue whenever it changes.
  useEffect(() => {
    if (!serviceId) return
    let cancelled = false
    setQueue(null)
    setNotice(null)
    fetchQueue(serviceId)
      .then((data) => {
        if (!cancelled) setQueue(data)
      })
      .catch(() => {
        if (!cancelled) setError('Could not load the queue. Try refreshing the page.')
      })
    return () => {
      cancelled = true
    }
  }, [serviceId])

  const selectedService = services?.find((service) => service.id === serviceId) ?? null

  const handleServiceChange = (event: ChangeEvent<HTMLSelectElement>) => {
    navigate(`/admin/queue/${event.target.value}`)
  }

  const handleServeNext = async () => {
    if (!serviceId) return
    setBusy(true)
    setError(null)
    try {
      const { served, queue: nextQueue } = await serveNextQueueEntry(serviceId)
      setQueue(nextQueue)
      setNotice(served ? `Now serving ${served.name}.` : 'The queue is already empty.')
    } catch {
      setError('Could not serve the next person. Try again.')
    } finally {
      setBusy(false)
    }
  }

  const handleMove = async (entryId: string, direction: 'up' | 'down') => {
    if (!serviceId) return
    setBusy(true)
    setError(null)
    try {
      setQueue(await moveQueueEntry(serviceId, entryId, direction))
    } catch {
      setError('Could not reorder the queue. Try again.')
    } finally {
      setBusy(false)
    }
  }

  const handleRemove = async (entry: QueueEntry) => {
    if (!serviceId) return
    setBusy(true)
    setError(null)
    try {
      setQueue(await removeQueueEntry(serviceId, entry.id))
      setNotice(`Removed ${entry.name} from the queue.`)
    } catch {
      setError(`Could not remove ${entry.name}. Try again.`)
    } finally {
      setBusy(false)
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
            <Link to="/admin" className="btn btn-ghost">
              Back to dashboard
            </Link>
            <button type="button" className="btn btn-ghost" onClick={handleSignOut}>
              Sign out
            </button>
          </>
        }
      />

      <main className="admin-page__main">
        <section className="admin-intro glass" aria-labelledby="queue-title">
          <p className="admin-intro__eyebrow">Admin dashboard</p>
          <h1 id="queue-title">Queue management</h1>
          <p className="admin-intro__note">
            View who's waiting for a service, reorder or remove them, or call the next person in.
          </p>
          {services && services.length > 0 && (
            <SelectField
              label="Service"
              options={services.map((service) => ({ value: service.id, label: service.name }))}
              value={serviceId ?? ''}
              onChange={handleServiceChange}
            />
          )}
        </section>

        {error && (
          <div className="alert alert-error" role="alert">
            {error}
          </div>
        )}
        {notice && !error && (
          <div className="alert alert-success" role="status">
            {notice}
          </div>
        )}

        <section className="queue-panel glass" aria-label="Queue">
          {!selectedService || queue === null ? (
            !error && <p className="service-list__loading">Loading queue…</p>
          ) : (
            <>
              <div className="queue-panel__heading">
                <div>
                  <h2 className="queue-panel__title">{selectedService.name}</h2>
                  <p className="queue-panel__count">
                    {queue.length === 0
                      ? 'No one waiting'
                      : `${queue.length} ${queue.length === 1 ? 'person' : 'people'} waiting`}
                  </p>
                </div>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleServeNext}
                  disabled={busy || queue.length === 0}
                >
                  Serve next
                </button>
              </div>

              {queue.length === 0 ? (
                <p className="queue-panel__empty">Nobody is waiting for this service right now.</p>
              ) : (
                <ol className="queue-list">
                  {queue.map((entry, index) => (
                    <li key={entry.id} className="queue-row">
                      <span className="queue-row__position" aria-hidden="true">
                        {index + 1}
                      </span>
                      <div className="queue-row__info">
                        <span className="queue-row__name">{entry.name}</span>
                        <span className="queue-row__wait">Waiting {entry.joinedMinutesAgo} min</span>
                      </div>
                      <div className="queue-row__actions">
                        <button
                          type="button"
                          className="btn btn-ghost queue-row__icon-btn"
                          onClick={() => handleMove(entry.id, 'up')}
                          disabled={busy || index === 0}
                          aria-label={`Move ${entry.name} up`}
                        >
                          ↑
                        </button>
                        <button
                          type="button"
                          className="btn btn-ghost queue-row__icon-btn"
                          onClick={() => handleMove(entry.id, 'down')}
                          disabled={busy || index === queue.length - 1}
                          aria-label={`Move ${entry.name} down`}
                        >
                          ↓
                        </button>
                        <button type="button" className="btn btn-danger" onClick={() => handleRemove(entry)} disabled={busy}>
                          Remove
                        </button>
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </>
          )}
        </section>
      </main>
    </div>
  )
}
