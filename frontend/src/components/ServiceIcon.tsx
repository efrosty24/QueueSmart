import type { IconType } from 'react-icons'
import { LuFlaskConical, LuPill, LuStethoscope, LuSyringe } from 'react-icons/lu'
import type { ServiceId } from '../mocks/services'

const icons: Record<ServiceId, IconType> = {
  'sick-visit': LuStethoscope,
  'flu-shot': LuSyringe,
  'prescription-refill': LuPill,
  'lab-work': LuFlaskConical,
}

export function ServiceIcon({ serviceId, className }: { serviceId: ServiceId; className?: string }) {
  const Icon = icons[serviceId]
  return <Icon aria-hidden="true" className={className} />
}
