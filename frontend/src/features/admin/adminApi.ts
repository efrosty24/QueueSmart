export { createService, deleteService, fetchServices, setQueueStatus, updateService } from '../services/serviceApi'
export type { QueueStatus, PriorityLevel, Service, ServiceInput } from '../services/serviceApi'

// Queue actions remain a frontend demo until Module 3 is implemented.

// A single person waiting in a service's queue, front of the line first.
export type QueueEntry = {
  id: string
  name: string
  joinedMinutesAgo: number
}

const namePool = [
  'Jordan Lee',
  'Casey Kim',
  'Morgan Diaz',
  'Riley Chen',
  'Avery Patel',
  'Taylor Brooks',
  'Sam Okafor',
  'Jamie Novak',
  'Drew Alvarez',
  'Reese Nakamura',
]

function buildQueue(serviceId: string, count: number): QueueEntry[] {
  // Front of the line (index 0) has waited the longest.
  return Array.from({ length: count }, (_, index) => ({
    id: `${serviceId}-${index + 1}`,
    name: namePool[index % namePool.length],
    joinedMinutesAgo: (count - index) * 6,
  }))
}

const queues: Record<string, QueueEntry[]> = {
  'sick-visit': buildQueue('sick-visit', 4),
  'flu-shot': buildQueue('flu-shot', 2),
  'prescription-refill': [],
  'lab-work': [],
}

const simulateRequest = () => new Promise((resolve) => setTimeout(resolve, 400))

export async function fetchQueue(serviceId: string): Promise<QueueEntry[]> {
  await simulateRequest()
  const entries = queues[serviceId] ??= []
  return entries.map((entry) => ({ ...entry }))
}

export async function moveQueueEntry(
  serviceId: string,
  entryId: string,
  direction: 'up' | 'down',
): Promise<QueueEntry[]> {
  await simulateRequest()
  const entries = queues[serviceId]
  if (!entries) throw new Error(`Unknown service: ${serviceId}`)
  const index = entries.findIndex((entry) => entry.id === entryId)
  if (index === -1) throw new Error(`Unknown queue entry: ${entryId}`)
  const swapWith = direction === 'up' ? index - 1 : index + 1
  if (swapWith >= 0 && swapWith < entries.length) {
    const next = [...entries]
    ;[next[index], next[swapWith]] = [next[swapWith], next[index]]
    queues[serviceId] = next
  }
  return queues[serviceId].map((entry) => ({ ...entry }))
}

export async function removeQueueEntry(serviceId: string, entryId: string): Promise<QueueEntry[]> {
  await simulateRequest()
  const entries = queues[serviceId]
  if (!entries) throw new Error(`Unknown service: ${serviceId}`)
  queues[serviceId] = entries.filter((entry) => entry.id !== entryId)
  return queues[serviceId].map((entry) => ({ ...entry }))
}

// Removes and returns the person at the front of the line, simulating calling them in.
export async function serveNextQueueEntry(
  serviceId: string,
): Promise<{ served: QueueEntry | null; queue: QueueEntry[] }> {
  await simulateRequest()
  const entries = queues[serviceId]
  if (!entries) throw new Error(`Unknown service: ${serviceId}`)
  const [served, ...rest] = entries
  queues[serviceId] = rest
  return { served: served ? { ...served } : null, queue: rest.map((entry) => ({ ...entry })) }
}
