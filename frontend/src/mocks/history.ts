import type { ServiceId } from './services'

// Mock past queue entries for the signed-in patient. Replace with GET /me/history once the backend exists.

export type VisitOutcome = 'served' | 'left' | 'no-show'

export type PastVisit = {
  id: string
  ticket: string
  serviceId: ServiceId
  // When the patient joined the queue (ISO 8601).
  joinedAt: string
  outcome: VisitOutcome
  // Minutes between joining and being served or leaving. null for no-shows.
  waitedMinutes: number | null
}

export const mockHistory: PastVisit[] = [
  { id: 'v12', ticket: 'F-031', serviceId: 'flu-shot', joinedAt: '2026-09-28T10:05:00', outcome: 'served', waitedMinutes: 9 },
  { id: 'v11', ticket: 'S-007', serviceId: 'sick-visit', joinedAt: '2026-09-24T14:40:00', outcome: 'left', waitedMinutes: 22 },
  { id: 'v10', ticket: 'P-012', serviceId: 'prescription-refill', joinedAt: '2026-09-19T09:15:00', outcome: 'served', waitedMinutes: 14 },
  { id: 'v9', ticket: 'L-004', serviceId: 'lab-work', joinedAt: '2026-09-15T08:30:00', outcome: 'served', waitedMinutes: 18 },
  { id: 'v8', ticket: 'S-022', serviceId: 'sick-visit', joinedAt: '2026-09-10T16:10:00', outcome: 'no-show', waitedMinutes: null },
  { id: 'v7', ticket: 'S-015', serviceId: 'sick-visit', joinedAt: '2026-09-08T11:25:00', outcome: 'served', waitedMinutes: 41 },
  { id: 'v6', ticket: 'P-003', serviceId: 'prescription-refill', joinedAt: '2026-09-02T13:00:00', outcome: 'served', waitedMinutes: 7 },
  { id: 'v5', ticket: 'F-002', serviceId: 'flu-shot', joinedAt: '2026-08-28T15:45:00', outcome: 'left', waitedMinutes: 30 },
  { id: 'v4', ticket: 'L-010', serviceId: 'lab-work', joinedAt: '2026-08-26T09:50:00', outcome: 'served', waitedMinutes: 12 },
  { id: 'v3', ticket: 'S-031', serviceId: 'sick-visit', joinedAt: '2026-08-24T10:20:00', outcome: 'served', waitedMinutes: 35 },
  { id: 'v2', ticket: 'P-020', serviceId: 'prescription-refill', joinedAt: '2026-08-21T12:05:00', outcome: 'no-show', waitedMinutes: null },
  { id: 'v1', ticket: 'F-008', serviceId: 'flu-shot', joinedAt: '2026-08-19T11:00:00', outcome: 'served', waitedMinutes: 6 },
]
