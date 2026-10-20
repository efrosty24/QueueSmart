import { useEffect, useState, type ChangeEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { AppHeader } from '../../components/AppHeader'
import { SelectField } from '../../components/SelectField'
import { errorMessage } from '../../lib/api'
import { useAuth } from '../auth/AuthProvider'
import {
  fetchServiceQueue,
  fetchServices,
  serveNext,
  setEntryPriority,
  type QueueEntry,
  type Service,
} from './adminApi'
import './admin.css'

// How often to reload the line so new arrivals and departures appear.
const POLL_MS = 5000

// Lets admins view one service's queue at a time, mark people urgent, and call
// the next person in. Urgent patients go first; otherwise first come, first served.
export function QueueManagementPage() {
  const { user, token, signOut } = useAuth()
  const navigate = useNavigate()
  const { serviceId } = useParams<{ serviceId?: string }>()
  const [services, setServices] = useState<Service[] | null>(null)
  const [queue, setQueue] = useState<QueueEntry[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [now, setNow] = useState(Date.now)

  // Load services for this session; land on the first if the URL didn't name one.
  useEffect(() => {
    let cancelled = false
    fetchServices(token)
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
    // The service list does not depend on which queue is selected.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  // Load the selected service's queue whenever it changes, then keep it current.
  useEffect(() => {
    if (!serviceId) return
    let cancelled = false
    setQueue(null)
    setNotice(null)
    setError(null)
    const load = (initial: boolean) => {
      fetchServiceQueue(serviceId, token)
        .then((data) => {
          if (cancelled) return
          setQueue(data)
          setNow(Date.now())
        })
        .catch(() => {
          // Later polls keep the last known line; only a failed first load is an error.
          if (!cancelled && initial) setError('Could not load the queue. Try refreshing the page.')
        })
    }
    load(true)
    const timer = setInterval(() => load(false), POLL_MS)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [serviceId, token])

  const selectedService = services?.find((service) => service.id === serviceId) ?? null

  const handleServiceChange = (event: ChangeEvent<HTMLSelectElement>) => {
    navigate(`/admin/queue/${event.target.value}`)
  }

  const handleServeNext = async () => {
    if (!serviceId) return
    setBusy(true)
    setError(null)
    try {
      const { served, queue: nextQueue } = await serveNext(serviceId, token)
      setQueue(nextQueue)
      setNotice(served ? `Now serving ${served.email} (ticket ${served.ticket}).` : 'The queue is already empty.')
    } catch (err) {
      setError(errorMessage(err, 'Could not serve the next person. Try again.'))
    } finally {
      setBusy(false)
    }
  }

  const handleTogglePriority = async (entry: QueueEntry) => {
    if (!serviceId) return
    const priority = entry.priority === 'urgent' ? 'normal' : 'urgent'
    setBusy(true)
    setError(null)
    try {
      setQueue(await setEntryPriority(serviceId, entry.id, priority, token))
      setNotice(priority === 'urgent'
        ? `${entry.email} is marked urgent and moves ahead of routine patients.`
        : `${entry.email} is back in arrival order.`)
    } catch (err) {
      setError(errorMessage(err, `Could not change ${entry.email}'s priority. Try again.`))
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
            View who's waiting for a service and call the next person in. Patients are served in arrival
            order, except that anyone marked urgent goes first.
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
                  {queue.map((entry) => (
                    <li key={entry.id} className="queue-row">
                      <span className="queue-row__position" aria-hidden="true">
                        {entry.position}
                      </span>
                      <div className="queue-row__info">
                        <span className="queue-row__name">
                          {entry.email}{' '}
                          {entry.priority === 'urgent' && <span className="badge badge-danger">Urgent</span>}
                        </span>
                        <span className="queue-row__wait">
                          Ticket {entry.ticket} · Waiting {minutesSince(entry.joinedAt, now)} min
                        </span>
                      </div>
                      <div className="queue-row__actions">
                        <button
                          type="button"
                          className="btn btn-ghost"
                          onClick={() => handleTogglePriority(entry)}
                          disabled={busy}
                          aria-pressed={entry.priority === 'urgent'}
                        >
                          {entry.priority === 'urgent' ? 'Mark routine' : 'Mark urgent'}
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

function minutesSince(iso: string, now: number) {
  return Math.max(0, Math.floor((now - Date.parse(iso)) / 60_000))
}
