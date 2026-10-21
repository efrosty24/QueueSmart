import type { PastVisit, VisitOutcome } from './historyApi'

export const outcomeLabels: Record<VisitOutcome, string> = {
  served: 'Served',
  left: 'Left queue',
  'no-show': 'No-show',
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
