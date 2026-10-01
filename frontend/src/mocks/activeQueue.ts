import type { ServiceId } from './services'

// Mock "live" queue entry for the signed-in patient. Replace with the backend's
// queue entry + real-time updates once they exist.

export type QueueEventKind = 'joined' | 'moved' | 'delayed' | 'almost-ready' | 'served'

export type QueueTimelineStep = {
  // Place in line, where 1 means next. null once the patient has been served.
  position: number | null
  kind: QueueEventKind
  message: string
}

export const mockActiveQueue = {
  ticket: 'S-014',
  serviceId: 'sick-visit' as ServiceId,
  location: 'Campus Health Center, front desk',
}

// What happens to the entry over time. The demo plays one step every DEMO_STEP_MS.
export const mockQueueTimeline: QueueTimelineStep[] = [
  { position: 5, kind: 'joined', message: 'You joined the Sick Visit queue at position 5.' },
  { position: 4, kind: 'moved', message: 'You moved up to position 4.' },
  {
    position: 5,
    kind: 'delayed',
    message: 'An urgent case was moved ahead of you, so your wait went up a little.',
  },
  { position: 4, kind: 'moved', message: 'You moved up to position 4.' },
  { position: 3, kind: 'moved', message: 'You moved up to position 3.' },
  { position: 2, kind: 'almost-ready', message: "You're almost up. Head to the clinic now." },
  { position: 1, kind: 'moved', message: "You're next in line." },
  { position: null, kind: 'served', message: 'You have been served. Thanks for visiting!' },
]

export const DEMO_STEP_MS = 15_000
