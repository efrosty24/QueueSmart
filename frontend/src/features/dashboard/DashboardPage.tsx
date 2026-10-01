import { LuArrowRight, LuClock, LuUsers } from 'react-icons/lu'
import { Link } from 'react-router'
import { PageHeader } from '../../components/PageHeader'
import { ServiceIcon } from '../../components/ServiceIcon'
import { formatDate, formatMinutes } from '../../lib/format'
import { services } from '../../mocks/services'
import { useAuth } from '../auth/AuthProvider'
import { getHistory } from '../history/history'
import { OutcomeBadge } from '../history/OutcomeBadge'
import { QueueStatusBadge } from '../queue/QueueStatusBadge'
import { useQueueStatus } from '../queue/useQueueStatus'
import './dashboard.css'

const RECENT_VISIT_COUNT = 3

// Landing page after sign-in: a snapshot of the current queue and recent visits.
export function DashboardPage() {
  const { user } = useAuth()
  const { queue } = useQueueStatus()
  // Read on every render so today's visit appears as soon as the queue finishes.
  const recentVisits = getHistory().slice(0, RECENT_VISIT_COUNT)

  return (
    <>
      <PageHeader title="Dashboard" description={user ? `Welcome back, ${user.email}` : undefined} />

      <div className="dashboard-grid">
        <section className="dashboard-card glass" aria-labelledby="dashboard-queue-title">
          <div className="dashboard-card__header">
            <h2 id="dashboard-queue-title">Current queue</h2>
            <QueueStatusBadge status={queue.status} />
          </div>

          <div className="dashboard-queue__service">
            <span className="dashboard-icon">
              <ServiceIcon serviceId={queue.service.id} />
            </span>
            <div>
              <p className="dashboard-queue__name">{queue.service.name}</p>
              <p className="dashboard-muted">Ticket {queue.ticket}</p>
            </div>
          </div>

          {queue.status === 'served' ? (
            <p className="dashboard-muted">You've been served. Thanks for visiting!</p>
          ) : (
            <dl className="dashboard-queue__stats">
              <div>
                <dt>Position</dt>
                <dd className="dashboard-queue__position">#{queue.position}</dd>
              </div>
              <div>
                <dt>
                  <LuClock aria-hidden="true" /> Wait
                </dt>
                <dd>{queue.peopleAhead === 0 ? "You're next" : `~${formatMinutes(queue.estimatedWaitMinutes)}`}</dd>
              </div>
              <div>
                <dt>
                  <LuUsers aria-hidden="true" /> Ahead
                </dt>
                <dd>{queue.peopleAhead}</dd>
              </div>
            </dl>
          )}

          <Link to="/queue" className="dashboard-link">
            View queue status <LuArrowRight aria-hidden="true" />
          </Link>
        </section>

        <section className="dashboard-card glass" aria-labelledby="dashboard-history-title">
          <div className="dashboard-card__header">
            <h2 id="dashboard-history-title">Recent visits</h2>
          </div>

          <ul className="dashboard-visits">
            {recentVisits.map((visit) => (
              <li key={visit.id} className="dashboard-visit">
                <span className="dashboard-icon dashboard-icon--small">
                  <ServiceIcon serviceId={visit.serviceId} />
                </span>
                <span className="dashboard-visit__text">
                  <span className="dashboard-visit__name">{services[visit.serviceId].name}</span>
                  <span className="dashboard-muted">{formatDate(new Date(visit.joinedAt))}</span>
                </span>
                <OutcomeBadge outcome={visit.outcome} />
              </li>
            ))}
          </ul>

          <Link to="/history" className="dashboard-link">
            See all history <LuArrowRight aria-hidden="true" />
          </Link>
        </section>
      </div>
    </>
  )
}
