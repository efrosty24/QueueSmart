import { apiRequest } from '../../lib/api'

export type AppNotification = {
  id: string
  entryId: string
  ticket: string
  serviceId: string
  serviceName: string
  kind: 'joined' | 'moved' | 'delayed' | 'almost-ready' | 'served' | 'left'
  category: 'queue' | 'status'
  title: string
  message: string
  at: number
  read: boolean
}

type NotificationResponse = Omit<AppNotification, 'at'> & { at: string }

export async function fetchNotifications(token: string | null): Promise<AppNotification[]> {
  const items = await apiRequest<NotificationResponse[]>('/notifications', { token })
  return items.map((item) => ({ ...item, at: Date.parse(item.at) }))
}

export function setNotificationRead(id: string, token: string | null): Promise<NotificationResponse> {
  return apiRequest(`/notifications/${encodeURIComponent(id)}/read`, {
    method: 'PATCH', body: { read: true }, token,
  })
}

export function markAllNotificationsRead(token: string | null): Promise<void> {
  return apiRequest('/notifications/read-all', { method: 'POST', token })
}
