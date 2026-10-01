import type { IconType } from 'react-icons'
import { LuCircleCheck, LuDoorOpen, LuUserX } from 'react-icons/lu'
import type { VisitOutcome } from '../../mocks/history'
import { outcomeLabels } from './history'

const styles: Record<VisitOutcome, { className: string; icon: IconType }> = {
  served: { className: 'badge-success', icon: LuCircleCheck },
  left: { className: 'badge-neutral', icon: LuDoorOpen },
  'no-show': { className: 'badge-danger', icon: LuUserX },
}

export function OutcomeBadge({ outcome }: { outcome: VisitOutcome }) {
  const { className, icon: Icon } = styles[outcome]
  return (
    <span className={`badge ${className}`}>
      <Icon aria-hidden="true" />
      {outcomeLabels[outcome]}
    </span>
  )
}
