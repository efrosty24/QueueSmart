import {
  DEMO_STEP_MS,
  mockActiveQueue,
  mockQueueTimeline,
  type QueueEventKind,
} from '../../mocks/activeQueue'
import { services, type Service } from '../../mocks/services'

export type QueueStatus = 'waiting' | 'almost-ready' | 'served'

// Positions at or below this count as "almost ready".
export const ALMOST_READY_POSITION = 2

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
  ticket: string
  location: string
  service: Service
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

// Builds the current state of the mock queue entry from when the demo started.
export function deriveQueueState(startedAt: number, now: number): QueueState {
  const lastStep = mockQueueTimeline.length - 1
  const stepIndex = Math.min(Math.max(0, Math.floor((now - startedAt) / DEMO_STEP_MS)), lastStep)
  const { position } = mockQueueTimeline[stepIndex]
  const service = services[mockActiveQueue.serviceId]
  const peopleAhead = position === null ? 0 : position - 1

  return {
    ticket: mockActiveQueue.ticket,
    location: mockActiveQueue.location,
    service,
    joinedAt: startedAt,
    position,
    peopleAhead,
    estimatedWaitMinutes: peopleAhead * service.expectedMinutes,
    status: statusForPosition(position),
    updates: mockQueueTimeline
      .slice(0, stepIndex + 1)
      .map((step, index) => ({ id: index, kind: step.kind, message: step.message, at: startedAt + index * DEMO_STEP_MS }))
      .reverse(),
  }
}
