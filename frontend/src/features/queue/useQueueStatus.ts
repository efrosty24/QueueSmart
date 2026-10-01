import { useEffect, useReducer, useState } from 'react'
import type { ServiceId } from '../../mocks/services'
import { useAuth } from '../auth/AuthProvider'
import { deriveQueueState } from './queueStatus'
import { joinService, leaveService, QUEUE_CHANGED, readQueueSession, startDemo } from './queueSession'

// The demo's start time lives in sessionStorage so the queue keeps progressing
// while the user moves between pages, and starts fresh in a new tab.
// TODO: replace with live data from the backend (polling or WebSocket).
export function useQueueStatus() {
  const { user } = useAuth()
  const email = user?.email ?? ''
  const [, refresh] = useReducer((value: number) => value + 1, 0)
  const [now, setNow] = useState(Date.now)

  useEffect(() => {
    const update = () => { setNow(Date.now()); refresh() }
    window.addEventListener(QUEUE_CHANGED, update)
    const timer = setInterval(update, 1000)
    return () => {
      window.removeEventListener(QUEUE_CHANGED, update)
      clearInterval(timer)
    }
  }, [])

  const { entry } = readQueueSession(email)
  return {
    now,
    queue: entry ? deriveQueueState(entry.joinedAt, now, entry) : null,
    joinQueue: (serviceId: ServiceId) => joinService(email, serviceId),
    leaveQueue: () => leaveService(email),
    restartDemo: () => startDemo(email),
  }
}
