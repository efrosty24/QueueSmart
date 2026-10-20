import { useEffect, useState } from 'react'
import { errorMessage } from '../../lib/api'
import { useAuth } from '../auth/AuthProvider'
import { fetchServices, type Service } from './serviceApi'

// Reload on navigation or tab focus so patients see administrators' changes.
export function useServices() {
  const { token } = useAuth()
  const [services, setServices] = useState<Service[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const load = () => {
      fetchServices(token)
        .then((data) => {
          if (cancelled) return
          setServices(data)
          setError(null)
        })
        .catch((err: unknown) => {
          if (!cancelled) setError(errorMessage(err, 'Could not load services. Try refreshing the page.'))
        })
        .finally(() => { if (!cancelled) setLoading(false) })
    }
    load()
    window.addEventListener('focus', load)
    return () => {
      cancelled = true
      window.removeEventListener('focus', load)
    }
  }, [token])

  return { services, loading, error }
}
