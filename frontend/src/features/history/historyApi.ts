import { apiRequest } from '../../lib/api'

export type VisitOutcome = 'served' | 'left' | 'no-show'
export type PastVisit = {
  id: string
  ticket: string
  serviceId: string
  serviceName: string
  joinedAt: string
  finishedAt: string
  outcome: VisitOutcome
  waitedMinutes: number
}

export function fetchHistory(token: string | null): Promise<PastVisit[]> {
  return apiRequest('/history', { token })
}
