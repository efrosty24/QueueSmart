import { useEffect, useState } from 'react'
import { errorMessage } from '../../lib/api'
import { useAuth } from '../auth/AuthProvider'
import { useQueue } from '../queue/QueueProvider'
import { fetchHistory, type PastVisit } from './historyApi'

// Fetch on navigation and queue completion, then poll for changes made in other browsers.
export function useHistory() {
  const { token } = useAuth()
  const { queue } = useQueue()
  const [visits, setVisits] = useState<PastVisit[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return
    let cancelled = false
    let version = 0
    const load = async () => {
      const request = ++version
      try {
        const next = await fetchHistory(token)
        if (cancelled || request !== version) return
        setVisits(next)
        setError(null)
      } catch (err) {
        if (!cancelled && request === version) setError(errorMessage(err, 'Could not load visit history.'))
      } finally {
        if (!cancelled && request === version) setLoading(false)
      }
    }
    void load()
    const timer = setInterval(() => { void load() }, 3000)
    window.addEventListener('focus', load)
    return () => {
      cancelled = true
      clearInterval(timer)
      window.removeEventListener('focus', load)
    }
  }, [token, queue?.id, queue?.status])

  return { visits, loading, error }
}
