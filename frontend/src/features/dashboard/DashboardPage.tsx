import { LuArrowRight, LuClock, LuPlus, LuUsers } from 'react-icons/lu'
import { Link } from 'react-router'
import { ClinicServiceCard } from '../../components/ClinicServiceCard'
import { PageHeader } from '../../components/PageHeader'
import { ServiceIcon } from '../../components/ServiceIcon'
import { formatDate, formatMinutes } from '../../lib/format'
import { services as demoServices } from '../../mocks/services'
import { useAuth } from '../auth/AuthProvider'
import { getHistory } from '../history/history'
import { OutcomeBadge } from '../history/OutcomeBadge'
import { NotificationsPanel } from '../notifications/NotificationsPanel'
import { useQueue } from '../queue/QueueProvider'
import { QueueStatusBadge } from '../queue/QueueStatusBadge'
import { useServices } from '../services/useServices'
import './dashboard.css'

const RECENT_VISIT_COUNT = 3

// Landing page after sign-in: current queue, recent visits, and notifications.
export function DashboardPage() {
  const { user } = useAuth()
  const { queue, now } = useQueue()
  const { services, loading, error } = useServices()
  // Read on every render so today's visit appears as soon as the queue finishes.
  const recentVisits = getHistory(now, user?.email).slice(0, RECENT_VISIT_COUNT)

  return (
    <>
      <PageHeader title="Dashboard" description={user ? `Welcome back, ${user.email}. Your campus clinic at a glance.` : undefined}
        actions={<Link to="/join-queue" className="btn btn-primary"><LuPlus aria-hidden="true" /> Join a queue</Link>} />

      <div className="dashboard-grid">
        <section
          className="dashboard-card glass"
          aria-labelledby="dashboard-queue-title"
        >
          <div className="dashboard-card__header">
            <h2 id="dashboard-queue-title">Current queue</h2>
            {queue && <QueueStatusBadge status={queue.status} />}
          </div>

          {queue ? <>
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
            <p className="dashboard-muted">
              You've been served. Thanks for visiting!
            </p>
          ) : (
            <dl className="dashboard-queue__stats">
              <div>
                <dt>Position</dt>
                <dd className="dashboard-queue__position">
                  #{queue.position}
                </dd>
              </div>

              <div>
                <dt>
                  <LuClock aria-hidden="true" /> Wait
                </dt>
                <dd>
                  {queue.peopleAhead === 0
                    ? "You're next"
                    : `~${formatMinutes(queue.estimatedWaitMinutes)}`}
                </dd>
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
          </> : <>
            <p className="dashboard-empty-title">You're not in a queue</p>
            <p className="dashboard-muted">Choose a clinic service below to check the wait and save your place in line.</p>
            <Link to="/join-queue" className="dashboard-link">Find a clinic service <LuArrowRight aria-hidden="true" /></Link>
          </>}
        </section>

        <NotificationsPanel preview />

        <section className="dashboard-services" aria-labelledby="dashboard-services-title">
          <div className="dashboard-section-heading">
            <div><h2 id="dashboard-services-title">Clinic services</h2><p className="dashboard-muted">Browse available services and estimated waits.</p></div>
            <span className="badge badge-success">{services.filter((service) => service.status === 'open').length} open</span>
          </div>
          {loading && <p role="status">Loading services…</p>}
          {error && <p className="alert alert-error" role="alert">{error}</p>}
          {!loading && !error && services.length === 0 && <p>No clinic services are available yet.</p>}
          <div className="dashboard-service-grid">
            {services.map((service) => (
              <ClinicServiceCard key={service.id} service={service}>
                {service.status === 'open'
                  ? <Link className="btn btn-ghost btn-block" to={`/join-queue?service=${service.id}`}>Select service <LuArrowRight aria-hidden="true" /></Link>
                  : <p className="dashboard-muted">This queue is currently closed.</p>}
              </ClinicServiceCard>
            ))}
          </div>
        </section>

        <section className="dashboard-card dashboard-recent glass" aria-labelledby="dashboard-history-title">
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
                  <span className="dashboard-visit__name">
                    {visit.serviceName ?? demoServices[visit.serviceId]?.name ?? 'Clinic service'}
                  </span>
                  <span className="dashboard-muted">
                    {formatDate(new Date(visit.joinedAt))}
                  </span>
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
