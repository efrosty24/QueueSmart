// NotificationsProvider component for managing app notifications.

import { createContext, useContext, useState, type ReactNode } from 'react'
import type { QueueEventKind } from '../../mocks/activeQueue'
import { useAuth } from '../auth/AuthProvider'
import { useQueue } from '../queue/QueueProvider'

type AppNotification = {
  id: string
  category: 'queue' | 'status'
  title: string
  message: string
  at: number
  read: boolean
}

type NotificationsContextValue = {
  notifications: AppNotification[]
  unreadCount: number
  markRead: (id: string) => void
  markAllRead: () => void
}

const titles: Record<QueueEventKind, string> = {
  joined: 'Waiting',
  moved: 'Position updated',
  delayed: 'Queue delayed',
  'almost-ready': 'Almost ready',
  served: 'Served',
}

const NotificationsContext =
  createContext<NotificationsContextValue | null>(null)

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const { queue } = useQueue()
  const [readIds, setReadIds] = useState<Set<string>>(() => new Set())

  const ticket = queue ? `Ticket ${queue.ticket}` : ''
  const service = queue?.service.name ?? ''

  const adminMessages: Record<QueueEventKind, string> = {
    joined: `${ticket} joined the ${service} queue.`,
    moved: `${ticket} moved forward in the ${service} queue.`,
    delayed: `An urgent case changed the queue order for ${service}.`,
    'almost-ready': `${ticket} is almost ready for ${service}.`,
    served: `${ticket} was marked as served for ${service}.`,
  }

  const notifications = queue ? queue.updates.map<AppNotification>((update) => {
    const id = `${queue.joinedAt}:${queue.ticket}:${update.id}`

    return {
      id,
      category:
        update.kind === 'moved' || update.kind === 'delayed'
          ? 'queue'
          : 'status',
      title: titles[update.kind],
      message:
        user?.role === 'admin'
          ? adminMessages[update.kind]
          : `${service}: ${update.message}`,
      at: update.at,
      read: readIds.has(id),
    }
  }) : []

  const unreadCount = notifications.filter((item) => !item.read).length

  const markRead = (id: string) => {
    setReadIds((current) => new Set([...current, id]))
  }

  const markAllRead = () => {
    setReadIds(
      (current) => new Set([...current, ...notifications.map((item) => item.id)]),
    )
  }

  return (
    <NotificationsContext.Provider
      value={{ notifications, unreadCount, markRead, markAllRead }}
    >
      {children}
    </NotificationsContext.Provider>
  )
}

// eslint-disable-next-line react/only-export-components
export function useNotifications() {
  const context = useContext(NotificationsContext)

  if (!context) {
    throw new Error(
      'useNotifications must be used inside NotificationsProvider',
    )
  }

  return context
}
