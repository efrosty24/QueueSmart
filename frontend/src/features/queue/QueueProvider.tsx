// Every useQueueStatus() call owns its own timer and restart state
// This wrapper gives the dashboard, queue page, and notifications one shared instance

import { createContext, useContext, type ReactNode } from 'react'
import { useQueueStatus } from './useQueueStatus'

const QueueContext =
  createContext<ReturnType<typeof useQueueStatus> | null>(null)

export function QueueProvider({ children }: { children: ReactNode }) {
  const value = useQueueStatus()

  return (
    <QueueContext.Provider value={value}>
      {children}
    </QueueContext.Provider>
  )
}

// eslint-disable-next-line react/only-export-components
export function useQueue() {
  const context = useContext(QueueContext)

  if (!context) {
    throw new Error('useQueue must be used inside QueueProvider')
  }

  return context
}