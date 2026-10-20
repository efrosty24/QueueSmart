import type { PastVisit } from '../../mocks/history'
import { services } from '../../mocks/services'
import type { Service } from '../services/serviceApi'
import { deriveQueueState, type QueueEntry } from './queueStatus'

type QueueSession = { entry: QueueEntry | null; visits: PastVisit[] }
const sessions = new Map<string, QueueSession>()
export const QUEUE_CHANGED = 'queuesmart-queue-changed'

function storageKey(email: string) {
  return `queuesmart-queue-v2:${email.trim().toLowerCase()}`
}

function isEntry(value: unknown): value is QueueEntry {
  if (!value || typeof value !== 'object') return false
  const entry = value as Partial<QueueEntry>
  return typeof entry.id === 'string' && typeof entry.ticket === 'string'
    && typeof entry.serviceId === 'string'
    && (entry.service === undefined ? Object.hasOwn(services, entry.serviceId)
      : entry.service !== null && typeof entry.service === 'object'
        && entry.service.id === entry.serviceId && typeof entry.service.name === 'string'
        && typeof entry.service.expectedMinutes === 'number' && Number.isFinite(entry.service.expectedMinutes)
        && entry.service.expectedMinutes >= 1 && entry.service.expectedMinutes <= 480
        && ['low', 'medium', 'high'].includes(entry.service.priority))
    && typeof entry.joinedAt === 'number' && Number.isFinite(entry.joinedAt) && entry.joinedAt > 0
    && typeof entry.initialPosition === 'number' && Number.isInteger(entry.initialPosition)
    && entry.initialPosition > 0 && entry.initialPosition <= 100
    && (entry.demo === undefined || typeof entry.demo === 'boolean')
}

function isVisit(value: unknown): value is PastVisit {
  if (!value || typeof value !== 'object') return false
  const visit = value as Partial<PastVisit>
  return typeof visit.id === 'string' && typeof visit.ticket === 'string'
    && typeof visit.serviceId === 'string' && visit.serviceId.length > 0
    && (visit.serviceName === undefined || typeof visit.serviceName === 'string')
    && typeof visit.joinedAt === 'string' && Number.isFinite(Date.parse(visit.joinedAt))
    && (visit.outcome === 'served' || visit.outcome === 'left' || visit.outcome === 'no-show')
    && (visit.waitedMinutes === null || (typeof visit.waitedMinutes === 'number'
      && Number.isFinite(visit.waitedMinutes) && visit.waitedMinutes >= 0))
}

// Per student and per tab; memory fallback also works with browser storage blocked.
export function readQueueSession(email: string): QueueSession {
  const key = storageKey(email)
  const cached = sessions.get(key)
  if (cached) return cached
  let session: QueueSession = { entry: null, visits: [] }
  try {
    const saved = JSON.parse(sessionStorage.getItem(key) ?? 'null')
    if (saved && (saved.entry === null || isEntry(saved.entry)) && Array.isArray(saved.visits)) {
      session = { entry: saved.entry, visits: saved.visits.filter(isVisit) }
    }
  } catch { /* Start with an empty queue if storage is blocked or invalid. */ }
  sessions.set(key, session)
  return session
}

function save(email: string, session: QueueSession) {
  const key = storageKey(email)
  sessions.set(key, session)
  try { sessionStorage.setItem(key, JSON.stringify(session)) } catch { /* Keep in-memory state. */ }
  window.dispatchEvent(new Event(QUEUE_CHANGED))
}

function pastVisit(entry: QueueEntry, outcome: 'served' | 'left', at: number): PastVisit {
  return {
    id: entry.id, ticket: entry.ticket, serviceId: entry.serviceId,
    serviceName: entry.service?.name ?? services[entry.serviceId]?.name,
    joinedAt: new Date(entry.joinedAt).toISOString(), outcome,
    waitedMinutes: Math.max(0, Math.round((at - entry.joinedAt) / 60_000)),
  }
}

export function queueVisits(email: string, now = Date.now()): PastVisit[] {
  const { entry, visits } = readQueueSession(email)
  if (!entry) return visits
  const queue = deriveQueueState(entry.joinedAt, now, entry)
  if (queue.status !== 'served') return visits
  return [...visits, pastVisit(entry, 'served', queue.updates[0].at)]
}

export function joinService(email: string, service: Service, now = Date.now()): string | undefined {
  if (service.status !== 'open') return 'This clinic queue is closed.'
  const serviceId = service.id
  const session = readQueueSession(email)
  if (session.entry && deriveQueueState(session.entry.joinedAt, now, session.entry).status !== 'served') {
    return 'You already have an active queue. Leave it before joining another service.'
  }
  const id = crypto.randomUUID()
  save(email, {
    visits: queueVisits(email, now),
    entry: {
      id, serviceId, joinedAt: now, initialPosition: service.queueLength + 1,
      service: { id: serviceId, name: service.name, expectedMinutes: service.expectedDurationMinutes, priority: service.priority },
      ticket: `${serviceId[0].toUpperCase()}-${id.slice(0, 4).toUpperCase()}`,
    },
  })
}

export function leaveService(email: string, now = Date.now()): boolean {
  const session = readQueueSession(email)
  if (!session.entry) return false
  const queue = deriveQueueState(session.entry.joinedAt, now, session.entry)
  if (queue.status === 'served') return false
  save(email, { entry: null, visits: [...session.visits, pastVisit(session.entry, 'left', now)] })
  return true
}

export function startDemo(email: string) {
  const now = Date.now()
  const session = readQueueSession(email)
  save(email, {
    visits: queueVisits(email, now),
    entry: session.entry && deriveQueueState(session.entry.joinedAt, now, session.entry).status !== 'served'
      ? { ...session.entry, joinedAt: now }
      : { id: crypto.randomUUID(), serviceId: 'sick-visit', ticket: 'S-014', joinedAt: now, initialPosition: 5, demo: true },
  })
}
