import type { PastVisit } from '../../mocks/history'
import type { QueueState } from './queueStatus'

// The backend owns the live queue. Finished visits stay in this tab until the
// history module (a later assignment) stores them on the server.
const visitsByKey = new Map<string, PastVisit[]>()

function storageKey(email: string) {
  return `queuesmart-visits-v1:${email.trim().toLowerCase()}`
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
export function queueVisits(email: string): PastVisit[] {
  const key = storageKey(email)
  const cached = visitsByKey.get(key)
  if (cached) return cached
  let visits: PastVisit[] = []
  try {
    const saved = JSON.parse(sessionStorage.getItem(key) ?? 'null')
    if (Array.isArray(saved)) visits = saved.filter(isVisit)
  } catch { /* Start with no visits if storage is blocked or invalid. */ }
  visitsByKey.set(key, visits)
  return visits
}

// Saves a finished queue entry once, however many times it is reported.
export function recordVisit(email: string, queue: QueueState, outcome: 'served' | 'left', endedAt = Date.now()) {
  const visits = queueVisits(email)
  if (visits.some((visit) => visit.id === queue.id)) return
  const next = [...visits, {
    id: queue.id, ticket: queue.ticket, serviceId: queue.service.id, serviceName: queue.service.name,
    joinedAt: new Date(queue.joinedAt).toISOString(), outcome,
    waitedMinutes: Math.max(0, Math.round((endedAt - queue.joinedAt) / 60_000)),
  }]
  const key = storageKey(email)
  visitsByKey.set(key, next)
  try { sessionStorage.setItem(key, JSON.stringify(next)) } catch { /* Keep in-memory visits. */ }
}
