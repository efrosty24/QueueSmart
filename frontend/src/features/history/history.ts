import { mockHistory, type PastVisit, type VisitOutcome } from '../../mocks/history'
import { loadSession } from '../auth/session'
import { queueVisits } from '../queue/queueSession'

export const outcomeLabels: Record<VisitOutcome, string> = {
  served: 'Served',
  left: 'Left queue',
  'no-show': 'No-show',
}

// Past visits, newest first. Once clinic staff serve the patient (or they
// leave a queue), today's visit shows up here too.
// `now` is unused, but callers pass it so the list re-reads as the queue changes.
export function getHistory(_now = Date.now(), email = loadSession()?.email ?? ''): PastVisit[] {
  const visits = [...mockHistory, ...queueVisits(email)]
  return visits.sort((a, b) => Date.parse(b.joinedAt) - Date.parse(a.joinedAt))
}

export function summarize(visits: PastVisit[]) {
  const served = visits.filter((visit) => visit.outcome === 'served')
  const waits = served.map((visit) => visit.waitedMinutes ?? 0)
  return {
    total: visits.length,
    served: served.length,
    averageWaitMinutes: waits.length ? Math.round(waits.reduce((sum, wait) => sum + wait, 0) / waits.length) : null,
  }
}
