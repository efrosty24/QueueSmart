import {
  DEMO_STEP_MS,
  mockActiveQueue,
  mockQueueTimeline,
  type QueueEventKind,
  type QueueTimelineStep,
} from '../../mocks/activeQueue'
import { services, type Service, type ServiceId } from '../../mocks/services'

export type QueueEntry = {
  id: string
  ticket: string
  serviceId: ServiceId
  joinedAt: number
  initialPosition: number
  demo?: boolean
}

function timelineFor(entry?: QueueEntry): QueueTimelineStep[] {
  if (!entry || entry.demo) return mockQueueTimeline
  const timeline: QueueTimelineStep[] = [{
    position: entry.initialPosition,
    kind: 'joined',
    message: `You joined the ${services[entry.serviceId].name} queue at position ${entry.initialPosition}.`,
  }]
  for (let position = entry.initialPosition - 1; position >= 1; position--) {
    timeline.push({
      position,
      kind: position === ALMOST_READY_POSITION ? 'almost-ready' : 'moved',
      message: position === 1 ? "You're next in line." : position === ALMOST_READY_POSITION
        ? "You're almost up. Head to the clinic now." : `You moved up to position ${position}.`,
    })
  }
  timeline.push({ position: null, kind: 'served', message: 'You have been served. Thanks for visiting!' })
  return timeline
}

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
export function deriveQueueState(startedAt: number, now: number, entry?: QueueEntry): QueueState {
  const timeline = timelineFor(entry)
  const lastStep = timeline.length - 1
  const stepIndex = Math.min(Math.max(0, Math.floor((now - startedAt) / DEMO_STEP_MS)), lastStep)
  const { position } = timeline[stepIndex]
  const service = services[entry?.serviceId ?? mockActiveQueue.serviceId]
  const peopleAhead = position === null ? 0 : position - 1

  return {
    ticket: entry?.ticket ?? mockActiveQueue.ticket,
    location: mockActiveQueue.location,
    service,
    joinedAt: startedAt,
    position,
    peopleAhead,
    estimatedWaitMinutes: peopleAhead * service.expectedMinutes,
    status: statusForPosition(position),
    updates: timeline
      .slice(0, stepIndex + 1)
      .map((step, index) => ({ id: index, kind: step.kind, message: step.message, at: startedAt + index * DEMO_STEP_MS }))
      .reverse(),
  }
}
