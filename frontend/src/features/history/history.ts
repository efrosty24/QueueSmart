import { DEMO_STEP_MS, mockActiveQueue, mockQueueTimeline } from '../../mocks/activeQueue'
import { mockHistory, type PastVisit, type VisitOutcome } from '../../mocks/history'
import { deriveQueueState } from '../queue/queueStatus'
import { peekDemoStart } from '../queue/useQueueStatus'

export const outcomeLabels: Record<VisitOutcome, string> = {
  served: 'Served',
  left: 'Left queue',
  'no-show': 'No-show',
}

// Past visits, newest first. Once the demo queue on the Queue status page
// reaches "served", today's visit shows up here too.
export function getHistory(now = Date.now()): PastVisit[] {
  const visits = [...mockHistory]
  const demoStart = peekDemoStart()

  if (demoStart && deriveQueueState(demoStart, now).status === 'served') {
    // Wait = how long the demo took to reach "served".
    const demoMinutes = Math.max(1, Math.round(((mockQueueTimeline.length - 1) * DEMO_STEP_MS) / 60_000))
    visits.push({
      id: 'current-demo',
      ticket: mockActiveQueue.ticket,
      serviceId: mockActiveQueue.serviceId,
      joinedAt: new Date(demoStart).toISOString(),
      outcome: 'served',
      waitedMinutes: demoMinutes,
    })
  }

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
