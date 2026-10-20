import type { ReactNode } from 'react'
import { LuClock, LuUsers } from 'react-icons/lu'
import { formatMinutes } from '../lib/format'
import type { Service } from '../features/services/serviceApi'
import { ServiceIcon } from './ServiceIcon'
import './ClinicServiceCard.css'

export function ClinicServiceCard({ service, children }: { service: Service; children?: ReactNode }) {
  const isOpen = service.status === 'open'
  return (
    <article className="clinic-service glass">
      <div className="clinic-service__header">
        <span className="clinic-service__icon"><ServiceIcon serviceId={service.id} /></span>
        <span className={`badge ${isOpen ? 'badge-success' : 'badge-neutral'}`}>
          {isOpen ? 'Open' : 'Closed'}
        </span>
      </div>
      <h3>{service.name}</h3>
      <p className="clinic-service__description">{service.description}</p>
      <dl className="clinic-service__details">
        <div><dt><LuClock aria-hidden="true" /> Typical visit</dt><dd>{formatMinutes(service.expectedDurationMinutes)}</dd></div>
        <div><dt><LuUsers aria-hidden="true" /> Students waiting</dt><dd>{service.queueLength}</dd></div>
        <div><dt>Estimated wait</dt><dd>{isOpen
          ? service.estimatedWaitMinutes === 0 ? 'No wait' : `~${formatMinutes(service.estimatedWaitMinutes)}`
          : 'Unavailable'}</dd></div>
      </dl>
      {children && <div className="clinic-service__action">{children}</div>}
    </article>
  )
}
