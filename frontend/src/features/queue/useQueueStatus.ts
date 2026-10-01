import { useEffect, useState } from 'react'
import { deriveQueueState } from './queueStatus'

// The demo's start time lives in sessionStorage so the queue keeps progressing
// while the user moves between pages, and starts fresh in a new tab.
// TODO: replace with live data from the backend (polling or WebSocket).
const DEMO_START_KEY = 'queuesmart-demo-queue-start'

// Reads the demo start without creating one (for pages that only look at the result).
export function peekDemoStart(): number | null {
  try {
    const stored = Number(sessionStorage.getItem(DEMO_START_KEY))
    return stored > 0 ? stored : null
  } catch {
    return null
  }
}

function readDemoStart() {
  const existing = peekDemoStart()
  if (existing) return existing
  try {
    const now = Date.now()
    sessionStorage.setItem(DEMO_START_KEY, String(now))
    return now
  } catch {
    return Date.now()
  }
}

export function useQueueStatus() {
  const [startedAt, setStartedAt] = useState(readDemoStart)
  const [now, setNow] = useState(Date.now)

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [])

  const restartDemo = () => {
    const restartAt = Date.now()
    try {
      sessionStorage.setItem(DEMO_START_KEY, String(restartAt))
    } catch {
      // Not persisted; the restart still applies to this page.
    }
    setStartedAt(restartAt)
    setNow(restartAt)
  }

  return { queue: deriveQueueState(startedAt, now), restartDemo }
}
