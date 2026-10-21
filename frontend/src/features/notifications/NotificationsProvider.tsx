import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { errorMessage } from '../../lib/api'
import { useAuth } from '../auth/AuthProvider'
import { useQueue } from '../queue/QueueProvider'
import { fetchNotifications, markAllNotificationsRead, setNotificationRead, type AppNotification } from './notificationsApi'

type NotificationsContextValue = {
  notifications: AppNotification[]
  unreadCount: number
  loading: boolean
  error: string | null
  markRead: (id: string) => Promise<void>
  markAllRead: () => Promise<void>
}

const NotificationsContext = createContext<NotificationsContextValue | null>(null)

// The backend owns both the notification feed and read state, even across logins.
export function NotificationsProvider({ children }: { children: ReactNode }) {
  const { token } = useAuth()
  const { queue } = useQueue()
  const [notifications, setNotifications] = useState<AppNotification[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const requestVersion = useRef(0)

  const refresh = useCallback(async (isActive: () => boolean = () => true) => {
    const version = ++requestVersion.current
    const isLatest = () => isActive() && version === requestVersion.current
    try {
      const items = await fetchNotifications(token)
      if (!isLatest()) return
      setNotifications(items)
      setError(null)
    } catch (err) {
      if (isLatest()) setError(errorMessage(err, 'Could not load notifications.'))
    } finally {
      if (isLatest()) setLoading(false)
    }
  }, [token])

  useEffect(() => {
    if (!token) return
    let cancelled = false
    const load = () => { void refresh(() => !cancelled) }
    load()
    const timer = setInterval(load, 3000)
    window.addEventListener('focus', load)
    return () => {
      cancelled = true
      clearInterval(timer)
      window.removeEventListener('focus', load)
    }
  }, [refresh, token, queue?.id, queue?.status])

  async function markRead(id: string) {
    ++requestVersion.current
    try {
      await setNotificationRead(id, token)
      await refresh()
    } catch (err) {
      setError(errorMessage(err, 'Could not mark the notification as read.'))
    }
  }

  async function markAllRead() {
    ++requestVersion.current
    try {
      await markAllNotificationsRead(token)
      await refresh()
    } catch (err) {
      setError(errorMessage(err, 'Could not mark notifications as read.'))
    }
  }

  return (
    <NotificationsContext.Provider value={{ notifications, unreadCount: notifications.filter((item) => !item.read).length,
      loading, error, markRead, markAllRead }}>
      {children}
    </NotificationsContext.Provider>
  )
}

// eslint-disable-next-line react/only-export-components
export function useNotifications() {
  const context = useContext(NotificationsContext)
  if (!context) throw new Error('useNotifications must be used inside NotificationsProvider')
  return context
}
