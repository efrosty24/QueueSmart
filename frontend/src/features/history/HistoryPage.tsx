import { useState } from 'react'
import { LuInbox } from 'react-icons/lu'
import { PageHeader } from '../../components/PageHeader'
import { ServiceIcon } from '../../components/ServiceIcon'
import { formatDate, formatMinutes, formatTime } from '../../lib/format'
import type { VisitOutcome } from '../../mocks/history'
import { services } from '../../mocks/services'
import { useAuth } from '../auth/AuthProvider'
import { useQueueStatus } from '../queue/useQueueStatus'
import { getHistory, outcomeLabels, summarize } from './history'
import { OutcomeBadge } from './OutcomeBadge'
import './history.css'

type Filter = 'all' | VisitOutcome

const filters: { value: Filter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'served', label: outcomeLabels.served },
  { value: 'left', label: outcomeLabels.left },
  { value: 'no-show', label: outcomeLabels['no-show'] },
]

export function HistoryPage() {
  const { user } = useAuth()
  // Keep completed visits current even when this page stays open.
  const { now } = useQueueStatus()
  const visits = getHistory(now, user?.email)
  const [filter, setFilter] = useState<Filter>('all')
  const summary = summarize(visits)
  const shown = filter === 'all' ? visits : visits.filter((visit) => visit.outcome === filter)

  return (
    <>
      <PageHeader title="History" description="Clinic queues you've joined before." />

      <dl className="history-summary">
        <div className="history-summary__item glass">
          <dt>Total visits</dt>
          <dd>{summary.total}</dd>
        </div>
        <div className="history-summary__item glass">
          <dt>Served</dt>
          <dd>{summary.served}</dd>
        </div>
        <div className="history-summary__item glass">
          <dt>Average wait</dt>
          <dd>{summary.averageWaitMinutes === null ? '—' : formatMinutes(summary.averageWaitMinutes)}</dd>
        </div>
      </dl>

      <section className="history-card glass" aria-labelledby="history-list-title">
        <div className="history-card__header">
          <h2 id="history-list-title">Past queues</h2>
          <div className="history-filters" role="group" aria-label="Filter by outcome">
            {filters.map(({ value, label }) => (
              <button
                key={value}
                type="button"
                className="history-filter"
                aria-pressed={filter === value}
                onClick={() => setFilter(value)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {shown.length === 0 ? (
          <div className="history-empty">
            <LuInbox aria-hidden="true" />
            <p>No visits match this filter.</p>
          </div>
        ) : (
          <table className="history-table" role="table">
            {/* Explicit roles keep table semantics when rows turn into cards on small screens. */}
            <caption className="visually-hidden">
              Past queues, newest first{filter === 'all' ? '' : `, showing ${outcomeLabels[filter]} only`}
            </caption>
            <thead role="rowgroup">
              <tr role="row">
                <th scope="col" role="columnheader">Date</th>
                <th scope="col" role="columnheader">Service</th>
                <th scope="col" role="columnheader">Wait</th>
                <th scope="col" role="columnheader">Outcome</th>
              </tr>
            </thead>
            <tbody role="rowgroup">
              {shown.map((visit) => {
                const joined = new Date(visit.joinedAt)
                return (
                  <tr key={visit.id} role="row">
                    <td role="cell" data-label="Date">
                      <time dateTime={visit.joinedAt}>
                        <span className="history-date">{formatDate(joined)}</span>
                        <span className="history-time">{formatTime(joined)}</span>
                      </time>
                    </td>
                    <td role="cell" data-label="Service">
                      <span className="history-service">
                        <span className="history-service__icon">
                          <ServiceIcon serviceId={visit.serviceId} />
                        </span>
                        <span>
                          {services[visit.serviceId].name}
                          <span className="history-ticket">Ticket {visit.ticket}</span>
                        </span>
                      </span>
                    </td>
                    <td role="cell" data-label="Wait">{visit.waitedMinutes === null ? '—' : formatMinutes(visit.waitedMinutes)}</td>
                    <td role="cell" data-label="Outcome">
                      <OutcomeBadge outcome={visit.outcome} />
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </section>
    </>
  )
}
