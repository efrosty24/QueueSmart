import type { QueueEntryResponse, QueueEventKind } from './queueApi'

export type QueueStatus = 'waiting' | 'almost-ready' | 'served'

// Positions at or below this count as "almost ready" (matches the backend).
export const ALMOST_READY_POSITION = 2

export const CLINIC_LOCATION = 'Campus Health Center, front desk'

export const statusLabels: Record<QueueStatus, string> = {
  waiting: 'Waiting',
  'almost-ready': 'Almost ready',
  served: 'Served',
}

export type QueueUpdate = {
  id: number
  kind: QueueEventKind
  message: string
  at: number
}

export type QueueState = {
  id: string
  ticket: string
  location: string
  service: { id: string; name: string; expectedMinutes: number }
  joinedAt: number
  position: number | null
  peopleAhead: number
  estimatedWaitMinutes: number
  status: QueueStatus
  // Newest first.
  updates: QueueUpdate[]
}

export function statusForPosition(position: number | null): QueueStatus {
  if (position === null) return 'served'
  return position <= ALMOST_READY_POSITION ? 'almost-ready' : 'waiting'
}

// Shapes the backend's queue entry for the patient screens.
export function toQueueState(entry: QueueEntryResponse): QueueState {
  return {
    id: entry.id,
    ticket: entry.ticket,
    location: CLINIC_LOCATION,
    service: { id: entry.serviceId, name: entry.serviceName, expectedMinutes: entry.expectedDurationMinutes },
    joinedAt: Date.parse(entry.joinedAt),
    position: entry.position,
    peopleAhead: entry.peopleAhead,
    estimatedWaitMinutes: entry.estimatedWaitMinutes,
    status: entry.status === 'served' ? 'served' : statusForPosition(entry.position),
    updates: entry.updates.map((update) => ({ ...update, at: Date.parse(update.at) })),
  }
}
