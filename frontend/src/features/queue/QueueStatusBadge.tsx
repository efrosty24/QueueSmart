import type { IconType } from 'react-icons'
import { LuBell, LuCircleCheck, LuHourglass } from 'react-icons/lu'
import { statusLabels, type QueueStatus } from './queueStatus'

const styles: Record<QueueStatus, { className: string; icon: IconType }> = {
  waiting: { className: 'badge-primary', icon: LuHourglass },
  'almost-ready': { className: 'badge-warning', icon: LuBell },
  served: { className: 'badge-success', icon: LuCircleCheck },
}

export function QueueStatusBadge({ status }: { status: QueueStatus }) {
  const { className, icon: Icon } = styles[status]
  return (
    <span className={`badge ${className}`}>
      <Icon aria-hidden="true" />
      {statusLabels[status]}
    </span>
  )
}
