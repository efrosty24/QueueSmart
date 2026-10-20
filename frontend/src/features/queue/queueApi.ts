import { apiRequest } from '../../lib/api'

export type QueueEventKind = 'joined' | 'moved' | 'delayed' | 'almost-ready' | 'served'
// Urgent entries are served before normal ones; otherwise first come, first served.
export type EntryPriority = 'normal' | 'urgent'

export type QueueUpdateResponse = {
  id: number
  kind: QueueEventKind
  message: string
  at: string
}

export type QueueEntryResponse = {
  id: string
  ticket: string
  serviceId: string
  serviceName: string
  email: string
  priority: EntryPriority
  status: 'waiting' | 'served' | 'left'
  // 1 means next. null once the entry is no longer waiting.
  position: number | null
  peopleAhead: number
  estimatedWaitMinutes: number
  expectedDurationMinutes: number
  joinedAt: string
  // Newest first.
  updates: QueueUpdateResponse[]
}

const servicePath = (serviceId: string) => `/queues/${encodeURIComponent(serviceId)}`

// Patients

export function fetchMyQueue(token: string | null): Promise<QueueEntryResponse | null> {
  return apiRequest<QueueEntryResponse | null>('/queues/me', { token })
}

export function joinQueue(serviceId: string, token: string | null): Promise<QueueEntryResponse> {
  return apiRequest<QueueEntryResponse>(`${servicePath(serviceId)}/join`, { method: 'POST', token })
}

export function leaveQueue(token: string | null): Promise<void> {
  return apiRequest<void>('/queues/me', { method: 'DELETE', token })
}

// Admins

export function fetchServiceQueue(serviceId: string, token: string | null): Promise<QueueEntryResponse[]> {
  return apiRequest<QueueEntryResponse[]>(servicePath(serviceId), { token })
}

export function serveNext(
  serviceId: string,
  token: string | null,
): Promise<{ served: QueueEntryResponse | null; queue: QueueEntryResponse[] }> {
  return apiRequest(`${servicePath(serviceId)}/serve-next`, { method: 'POST', token })
}

export function setEntryPriority(
  serviceId: string,
  entryId: string,
  priority: EntryPriority,
  token: string | null,
): Promise<QueueEntryResponse[]> {
  return apiRequest<QueueEntryResponse[]>(`${servicePath(serviceId)}/entries/${encodeURIComponent(entryId)}`, {
    method: 'PATCH',
    body: { priority },
    token,
  })
}
