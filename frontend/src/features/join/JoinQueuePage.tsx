import { useState, type FormEvent } from 'react'
import { LuArrowRight, LuLogOut } from 'react-icons/lu'
import { Link, useSearchParams } from 'react-router'
import { ClinicServiceCard } from '../../components/ClinicServiceCard'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { PageHeader } from '../../components/PageHeader'
import { formatMinutes } from '../../lib/format'
import { serviceQueues } from '../../mocks/serviceQueues'
import { services, type ServiceId } from '../../mocks/services'
import { QueueStatusBadge } from '../queue/QueueStatusBadge'
import { useQueue } from '../queue/QueueProvider'
import './join.css'

export function JoinQueuePage() {
  const [params] = useSearchParams()
  const [selected, setSelected] = useState<ServiceId | ''>(() => {
    const requested = params.get('service') ?? ''
    return Object.hasOwn(services, requested) ? requested as ServiceId : ''
  })
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [confirmLeave, setConfirmLeave] = useState(false)
  const { queue, joinQueue, leaveQueue } = useQueue()
  const active = queue && queue.status !== 'served'

  function handleJoin(event: FormEvent) {
    event.preventDefault()
    setNotice('')
    if (!selected) { setError('Select a clinic service before joining.'); return }
    const issue = joinQueue(selected)
    setError(issue ?? '')
    if (!issue) setNotice(`You joined the ${services[selected].name} queue. Your position will update automatically.`)
  }

  function handleLeave() {
    const left = leaveQueue()
    setConfirmLeave(false)
    setError('')
    setNotice(left ? 'You left the queue. Your visit is saved to History, and you can join another service.'
      : 'Your visit has already finished. You can join another service.')
  }

  return (
    <>
      <PageHeader title="Join a queue" description="Choose the campus clinic service you need and check the wait before joining." />
      {notice && <p className="alert alert-success" role="status">{notice}</p>}
      <div className="join-layout">
        <section className="join-panel glass" aria-labelledby="join-service-title">
          <h2 id="join-service-title">Choose a clinic service</h2>
          <p className="join-muted">You can be in one service queue at a time. Wait times are estimates and may change.</p>
          <form className="join-form" onSubmit={handleJoin} noValidate>
            <div className="join-field">
              <label htmlFor="clinic-service">Clinic service <span className="join-muted">(required)</span></label>
              <select id="clinic-service" value={selected} required aria-invalid={Boolean(error)}
                aria-describedby={error ? 'join-error' : 'join-service-help'}
                onChange={(event) => { setSelected(event.target.value as ServiceId | ''); setError(''); setNotice('') }}>
                <option value="">Select a service</option>
                {Object.values(services).map((service) => (
                  <option key={service.id} value={service.id} disabled={!serviceQueues[service.id].open}>
                    {service.name}{serviceQueues[service.id].open ? '' : ' — closed'}
                  </option>
                ))}
              </select>
              <p id="join-service-help" className="join-muted">Closed services are unavailable to join.</p>
              {error && <p id="join-error" className="alert alert-error" role="alert">{error}</p>}
            </div>
            {selected && <ClinicServiceCard serviceId={selected} />}
            {active && <p className="alert alert-warning">You're already in the {queue.service.name} queue. Leave your current queue before joining another.</p>}
            <button className="btn btn-primary" type="submit" disabled={Boolean(active) || Boolean(selected && !serviceQueues[selected].open)}>
              Join queue <LuArrowRight aria-hidden="true" />
            </button>
          </form>
        </section>

        <section className="join-panel glass" aria-labelledby="join-current-title">
          <div className="join-panel__heading">
            <h2 id="join-current-title">Your current queue</h2>
            {queue && <QueueStatusBadge status={queue.status} />}
          </div>
          {queue ? (
            <>
              <h3>{queue.service.name}</h3>
              <p className="join-muted">Ticket {queue.ticket}</p>
              {active ? (
                <>
                  <dl className="join-stats">
                    <div><dt>Position</dt><dd>#{queue.position}</dd></div>
                    <div><dt>Estimated wait</dt><dd>{queue.peopleAhead === 0 ? "You're next" : `~${formatMinutes(queue.estimatedWaitMinutes)}`}</dd></div>
                  </dl>
                  <p className="join-muted" aria-live="polite">{queue.updates[0].message}</p>
                  <Link to="/queue" className="btn btn-primary">View queue status</Link>
                  <button type="button" className="btn btn-danger-hover" onClick={() => setConfirmLeave(true)}>
                    <LuLogOut aria-hidden="true" /> Leave queue
                  </button>
                </>
              ) : <p>Your visit is complete and saved to <Link to="/history">History</Link>. You can join another service.</p>}
            </>
          ) : <p className="join-muted">You're not in a queue yet. Select an open service to get started.</p>}
        </section>
      </div>
      <ConfirmDialog open={confirmLeave} title="Leave this queue?" tone="danger" confirmLabel="Leave queue"
        message={`You'll give up your place in the ${queue?.service.name ?? 'clinic'} queue. You can rejoin at the end of the line.`}
        onConfirm={handleLeave} onCancel={() => setConfirmLeave(false)} />
    </>
  )
}
