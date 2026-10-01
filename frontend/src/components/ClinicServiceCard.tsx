import type { ReactNode } from 'react'
import { LuClock, LuUsers } from 'react-icons/lu'
import { formatMinutes } from '../lib/format'
import { serviceQueues } from '../mocks/serviceQueues'
import { services, type ServiceId } from '../mocks/services'
import { ServiceIcon } from './ServiceIcon'
import './ClinicServiceCard.css'

export function ClinicServiceCard({ serviceId, children }: { serviceId: ServiceId; children?: ReactNode }) {
  const service = services[serviceId]
  const availability = serviceQueues[serviceId]
  return (
    <article className="clinic-service glass">
      <div className="clinic-service__header">
        <span className="clinic-service__icon"><ServiceIcon serviceId={serviceId} /></span>
        <span className={`badge ${availability.open ? 'badge-success' : 'badge-neutral'}`}>
          {availability.open ? 'Open' : 'Closed'}
        </span>
      </div>
      <h3>{service.name}</h3>
      <p className="clinic-service__description">{availability.description}</p>
      <dl className="clinic-service__details">
        <div><dt><LuClock aria-hidden="true" /> Typical visit</dt><dd>{formatMinutes(service.expectedMinutes)}</dd></div>
        <div><dt><LuUsers aria-hidden="true" /> Students waiting</dt><dd>{availability.waiting}</dd></div>
        <div><dt>Estimated wait</dt><dd>{availability.open
          ? availability.waiting === 0 ? 'No wait' : `~${formatMinutes(availability.waiting * service.expectedMinutes)}`
          : 'Unavailable'}</dd></div>
      </dl>
      {children && <div className="clinic-service__action">{children}</div>}
    </article>
  )
}
