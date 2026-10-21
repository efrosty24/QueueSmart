import { useCallback, useEffect, useState } from 'react'
import { ApiError, errorMessage } from '../../lib/api'
import type { Service } from '../services/serviceApi'
import { useAuth } from '../auth/AuthProvider'
import { fetchMyQueue, joinQueue, leaveQueue, type QueueEntryResponse } from './queueApi'
import { toQueueState } from './queueStatus'

// How often to ask the backend for the patient's place in line.
const POLL_MS = 3000

export function useQueueStatus() {
  const { token } = useAuth()
  const [entry, setEntry] = useState<QueueEntryResponse | null>(null)
  const [now, setNow] = useState(Date.now)

  const apply = useCallback((next: QueueEntryResponse | null) => {
    setEntry(next)
    setNow(Date.now())
  }, [])

  const refresh = useCallback(async () => {
    try {
      apply(await fetchMyQueue(token))
    } catch { /* Keep the last known state; the next poll tries again. */ }
  }, [apply, token])

  useEffect(() => {
    if (!token) return
    let cancelled = false
    const load = () => {
      fetchMyQueue(token)
        .then((next) => { if (!cancelled) apply(next) })
        .catch(() => { /* Keep the last known state; the next poll tries again. */ })
    }
    load()
    const timer = setInterval(load, POLL_MS)
    window.addEventListener('focus', load)
    return () => {
      cancelled = true
      clearInterval(timer)
      window.removeEventListener('focus', load)
    }
  }, [apply, token])

  const queue = entry ? toQueueState(entry) : null

  // Returns an error message, or undefined on success.
  async function join(service: Service): Promise<string | undefined> {
    if (service.status !== 'open') return 'This clinic queue is closed.'
    try {
      apply(await joinQueue(service.id, token))
    } catch (error) {
      return errorMessage(error, 'Could not join the queue. Try again.')
    }
  }

  // Returns an error message, or undefined once the patient has left.
  async function leave(): Promise<string | undefined> {
    if (!queue || queue.status === 'served') return 'Your visit has already finished. You can join another service.'
    try {
      await leaveQueue(token)
      apply(null)
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        await refresh()
        return 'Your visit has already finished. You can join another service.'
      }
      return errorMessage(error, 'Could not leave the queue. Try again.')
    }
  }

  return { now, queue, joinQueue: join, leaveQueue: leave }
}
