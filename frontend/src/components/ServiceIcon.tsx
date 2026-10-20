import type { IconType } from 'react-icons'
import { LuFlaskConical, LuPill, LuStethoscope, LuSyringe } from 'react-icons/lu'

const icons: Partial<Record<string, IconType>> = {
  'sick-visit': LuStethoscope,
  'flu-shot': LuSyringe,
  'prescription-refill': LuPill,
  'lab-work': LuFlaskConical,
}

export function ServiceIcon({ serviceId, className }: { serviceId: string; className?: string }) {
  const Icon = icons[serviceId] ?? LuStethoscope
  return <Icon aria-hidden="true" className={className} />
}
