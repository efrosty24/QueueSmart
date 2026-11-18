import { apiDownload, apiRequest } from '../../lib/api'

// Admin reports (GET /api/reports and /api/reports/export). Visits are filtered by the
// local date the patient joined the queue; tzOffset tells the server the viewer's time zone.

export type ReportFilters = {
  // YYYY-MM-DD, inclusive. Empty means no limit.
  start: string
  end: string
  // Empty means all services.
  serviceId: string
}

export type ReportSummary = {
  totalVisits: number
  served: number
  left: number
  uniquePatients: number
  averageWaitMinutes: number | null
  longestWaitMinutes: number | null
  servedRate: number | null
  waitingNow: number
  // Local hour 0-23 when the most patients joined.
  busiestHour: number | null
}

export type ServiceActivity = {
  serviceId: string
  name: string
  description: string
  expectedDurationMinutes: number | null
  priority: string | null
  status: 'open' | 'closed'
  archived: boolean
  waitingNow: number
  visits: number
  served: number
  left: number
  averageWaitMinutes: number | null
  longestWaitMinutes: number | null
}

export type PatientActivity = {
  userId: string
  name: string
  email: string
  visits: number
  served: number
  left: number
  averageWaitMinutes: number | null
  firstVisitAt: string | null
  lastVisitAt: string | null
  services: string[]
}

export type ReportVisit = {
  id: string
  ticket: string
  patientName: string
  email: string
  serviceId: string
  serviceName: string
  joinedAt: string
  finishedAt: string
  outcome: 'served' | 'left'
  waitedMinutes: number
}

export type Report = {
  generatedAt: string
  serviceName: string | null
  summary: ReportSummary
  services: ServiceActivity[]
  patients: PatientActivity[]
  visits: ReportVisit[]
}

export type ExportFormat = 'csv' | 'pdf'

function query(filters: ReportFilters, extra: Record<string, string> = {}) {
  const params = new URLSearchParams({ tzOffset: String(new Date().getTimezoneOffset()), ...extra })
  if (filters.start) params.set('start', filters.start)
  if (filters.end) params.set('end', filters.end)
  if (filters.serviceId) params.set('serviceId', filters.serviceId)
  return params.toString()
}

export function fetchReport(filters: ReportFilters, token: string | null) {
  return apiRequest<Report>(`/reports?${query(filters)}`, { token })
}

export function downloadReport(filters: ReportFilters, format: ExportFormat, token: string | null) {
  return apiDownload(`/reports/export?${query(filters, { format })}`, token, `queuesmart-report.${format}`)
}
