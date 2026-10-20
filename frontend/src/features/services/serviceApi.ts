import { apiRequest } from '../../lib/api'

export type QueueStatus = 'open' | 'closed'
export type PriorityLevel = 'low' | 'medium' | 'high'

export type ServiceInput = {
  name: string
  description: string
  expectedDurationMinutes: number
  priority: PriorityLevel
}

export type Service = ServiceInput & {
  id: string
  status: QueueStatus
  // Demo counts until queue management is connected in Module 3.
  queueLength: number
  estimatedWaitMinutes: number
}

export function fetchServices(token: string | null): Promise<Service[]> {
  return apiRequest<Service[]>('/services', { token })
}

export function createService(input: ServiceInput, token: string | null): Promise<Service> {
  return apiRequest<Service>('/services', { method: 'POST', body: input, token })
}

export function updateService(id: string, input: ServiceInput, token: string | null): Promise<Service> {
  return apiRequest<Service>(`/services/${encodeURIComponent(id)}`, { method: 'PUT', body: input, token })
}

export function setQueueStatus(id: string, status: QueueStatus, token: string | null): Promise<Service> {
  return apiRequest<Service>(`/services/${encodeURIComponent(id)}/status`, { method: 'PATCH', body: { status }, token })
}

export function deleteService(id: string, token: string | null): Promise<void> {
  return apiRequest<void>(`/services/${encodeURIComponent(id)}`, { method: 'DELETE', token })
}
