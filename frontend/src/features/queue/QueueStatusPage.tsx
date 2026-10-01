import type { IconType } from 'react-icons'
import {
  LuActivity,
  LuBell,
  LuCircleAlert,
  LuCircleCheck,
  LuClock,
  LuHourglass,
  LuListOrdered,
  LuMapPin,
  LuRefreshCw,
  LuUsers,
} from 'react-icons/lu'
import { Link } from 'react-router'
import { PageHeader } from '../../components/PageHeader'
import { ServiceIcon } from '../../components/ServiceIcon'
import { formatMinutes, formatTime } from '../../lib/format'
import { DEMO_STEP_MS, type QueueEventKind } from '../../mocks/activeQueue'
import { QueueStatusBadge } from './QueueStatusBadge'
import { statusLabels, type QueueState, type QueueStatus } from './queueStatus'
import { useQueue } from './QueueProvider'
import './queue.css'

const steps: { status: QueueStatus; icon: IconType }[] = [
  { status: 'waiting', icon: LuHourglass },
  { status: 'almost-ready', icon: LuBell },
  { status: 'served', icon: LuCircleCheck },
]

const updateIcons: Record<QueueEventKind, IconType> = {
  joined: LuListOrdered,
  moved: LuActivity,
  delayed: LuCircleAlert,
  'almost-ready': LuBell,
  served: LuCircleCheck,
}

export function QueueStatusPage() {
  const { queue, restartDemo } = useQueue()

  if (!queue) return (
    <>
      <PageHeader title="Queue status" description="Your place in line updates automatically." />
      <section className="queue-card glass">
        <h2 className="queue-card__title">You're not in a queue</h2>
        <p>Select a campus clinic service to see its wait time and join the queue.</p>
        <Link to="/join-queue" className="btn btn-primary">Find a clinic service</Link>
      </section>
      <p className="queue-demo-note">
        <button type="button" className="btn btn-ghost btn-pill" onClick={restartDemo}>
          <LuRefreshCw aria-hidden="true" /> Start queue demo
        </button>
      </p>
    </>
  )

  return (
    <>
      <PageHeader
        title="Queue status"
        description="Your place in line updates automatically."
        actions={<QueueStatusBadge status={queue.status} />}
      />

      {/* Screen readers hear each status change once, without re-reading the page. */}
      <p className="visually-hidden" aria-live="polite">
        {liveSummary(queue)}
      </p>

      <div className="queue-layout">
        <section className="queue-hero glass" aria-labelledby="queue-service">
          <div className="queue-hero__service">
            <span className="queue-hero__service-icon">
              <ServiceIcon serviceId={queue.service.id} />
            </span>
            <div>
              <h2 id="queue-service">{queue.service.name}</h2>
              <p>Ticket {queue.ticket}</p>
            </div>
          </div>

          {queue.status === 'served' ? (
            <div className="queue-hero__served">
              <LuCircleCheck aria-hidden="true" />
              <p>
                <strong>You've been served.</strong> This visit is saved to your{' '}
                <Link to="/history">history</Link>.
              </p>
            </div>
          ) : (
            <dl className="queue-stats">
              <div className="queue-stat queue-stat--position">
                <dt>Position</dt>
                <dd>
                  <span className="queue-stat__big">#{queue.position}</span>
                  <span className="queue-stat__sub">in line</span>
                </dd>
              </div>
              <div className="queue-stat">
                <dt>
                  <LuClock aria-hidden="true" /> Estimated wait
                </dt>
                <dd>{queue.peopleAhead === 0 ? "You're next" : `About ${formatMinutes(queue.estimatedWaitMinutes)}`}</dd>
              </div>
              <div className="queue-stat">
                <dt>
                  <LuUsers aria-hidden="true" /> People ahead
                </dt>
                <dd>{queue.peopleAhead}</dd>
              </div>
            </dl>
          )}

          {queue.status === 'almost-ready' && (
            <div className="alert alert-warning queue-hero__callout">
              <LuBell aria-hidden="true" />
              <span>
                <strong>Almost your turn.</strong> Please head to the clinic now.
              </span>
            </div>
          )}

          <ol className="queue-steps" aria-label="Visit progress">
            {steps.map(({ status, icon: Icon }, index) => {
              const currentIndex = steps.findIndex((step) => step.status === queue.status)
              const state = index < currentIndex ? 'done' : index === currentIndex ? 'current' : 'upcoming'
              return (
                <li
                  key={status}
                  className={`queue-step queue-step--${state}`}
                  aria-current={state === 'current' ? 'step' : undefined}
                >
                  <span className="queue-step__dot">
                    <Icon aria-hidden="true" />
                  </span>
                  <span className="queue-step__label">{statusLabels[status]}</span>
                </li>
              )
            })}
          </ol>
        </section>

        <section className="queue-card glass" aria-labelledby="queue-updates-title">
          <h2 id="queue-updates-title" className="queue-card__title">
            Status updates
          </h2>
          {/* Focusable so keyboard users can scroll a long list. */}
          <ol className="queue-updates" tabIndex={0} aria-labelledby="queue-updates-title">
            {queue.updates.map((update) => {
              const Icon = updateIcons[update.kind]
              return (
                <li key={update.id} className={`queue-update queue-update--${update.kind}`}>
                  <span className="queue-update__icon">
                    <Icon aria-hidden="true" />
                  </span>
                  <span className="queue-update__message">{update.message}</span>
                  <time className="queue-update__time" dateTime={new Date(update.at).toISOString()}>
                    {formatTime(update.at)}
                  </time>
                </li>
              )
            })}
          </ol>
        </section>

        <section className="queue-card glass" aria-labelledby="queue-details-title">
          <h2 id="queue-details-title" className="queue-card__title">
            Visit details
          </h2>
          <dl className="queue-details">
            <div>
              <dt>Joined</dt>
              <dd>{formatTime(queue.joinedAt)}</dd>
            </div>
            <div>
              <dt>Typical visit</dt>
              <dd>{queue.service.expectedMinutes} min per patient</dd>
            </div>
            <div>
              <dt>
                <LuMapPin aria-hidden="true" /> Where to go
              </dt>
              <dd>{queue.location}</dd>
            </div>
          </dl>
        </section>
      </div>

      <p className="queue-demo-note">
        Demo data: the queue moves forward every {DEMO_STEP_MS / 1000} seconds.
        <button type="button" className="btn btn-ghost btn-pill" onClick={restartDemo}>
          <LuRefreshCw aria-hidden="true" />
          Restart demo
        </button>
      </p>
    </>
  )
}

function liveSummary(queue: QueueState) {
  if (queue.status === 'served') return 'Status: served.'
  const wait = queue.peopleAhead === 0 ? "You're next." : `Estimated wait about ${formatMinutes(queue.estimatedWaitMinutes)}.`
  return `Status: ${statusLabels[queue.status]}. Position ${queue.position} in line. ${wait}`
}
