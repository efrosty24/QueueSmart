// Placeholder admin data, held in memory. There is no backend yet.
// TODO: replace with real calls to the queue endpoints once the backend exists.

export type QueueStatus = 'open' | 'closed'
export type PriorityLevel = 'low' | 'medium' | 'high'

export type Service = {
  id: string
  name: string
  description: string
  expectedDurationMinutes: number
  priority: PriorityLevel
  queueLength: number
  status: QueueStatus
}

// Fields an admin fills in on the create/edit form. queueLength and status are
// managed separately (joining a queue, opening/closing it).
export type ServiceInput = {
  name: string
  description: string
  expectedDurationMinutes: number
  priority: PriorityLevel
}

// A single person waiting in a service's queue, front of the line first.
export type QueueEntry = {
  id: string
  name: string
  joinedMinutesAgo: number
}

// Service records as stored; queueLength isn't kept here; it's derived from `queues` below.
type ServiceRecord = Omit<Service, 'queueLength'>

let services: ServiceRecord[] = [
  {
    id: 'general',
    name: 'General Checkup',
    description: 'Routine checkups and general health concerns.',
    expectedDurationMinutes: 20,
    priority: 'medium',
    status: 'open',
  },
  {
    id: 'pharmacy',
    name: 'Pharmacy Pickup',
    description: 'Pick up prescriptions ordered by a clinician.',
    expectedDurationMinutes: 5,
    priority: 'low',
    status: 'open',
  },
  {
    id: 'lab',
    name: 'Lab Draw',
    description: 'Blood draws and specimen collection for lab tests.',
    expectedDurationMinutes: 10,
    priority: 'medium',
    status: 'closed',
  },
  {
    id: 'counseling',
    name: 'Counseling Walk-in',
    description: 'Same-day mental health support, no appointment needed.',
    expectedDurationMinutes: 30,
    priority: 'high',
    status: 'open',
  },
]

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
  general: buildQueue('general', 8),
  pharmacy: buildQueue('pharmacy', 3),
  lab: buildQueue('lab', 0),
  counseling: buildQueue('counseling', 5),
}

function toService(record: ServiceRecord): Service {
  return { ...record, queueLength: queues[record.id]?.length ?? 0 }
}

const simulateRequest = () => new Promise((resolve) => setTimeout(resolve, 400))

export async function fetchServices(): Promise<Service[]> {
  await simulateRequest()
  return services.map(toService)
}

export async function setQueueStatus(id: string, status: QueueStatus): Promise<Service> {
  await simulateRequest()
  services = services.map((service) => (service.id === id ? { ...service, status } : service))
  const updated = services.find((service) => service.id === id)
  if (!updated) throw new Error(`Unknown service: ${id}`)
  return toService(updated)
}

// New services start closed with an empty queue until an admin opens them.
export async function createService(input: ServiceInput): Promise<Service> {
  await simulateRequest()
  const record: ServiceRecord = { id: crypto.randomUUID(), ...input, status: 'closed' }
  services = [...services, record]
  queues[record.id] = []
  return toService(record)
}

export async function updateService(id: string, input: ServiceInput): Promise<Service> {
  await simulateRequest()
  services = services.map((service) => (service.id === id ? { ...service, ...input } : service))
  const updated = services.find((service) => service.id === id)
  if (!updated) throw new Error(`Unknown service: ${id}`)
  return toService(updated)
}

export async function deleteService(id: string): Promise<void> {
  await simulateRequest()
  if (!services.some((service) => service.id === id)) throw new Error(`Unknown service: ${id}`)
  services = services.filter((service) => service.id !== id)
  delete queues[id]
}

export async function fetchQueue(serviceId: string): Promise<QueueEntry[]> {
  await simulateRequest()
  return (queues[serviceId] ?? []).map((entry) => ({ ...entry }))
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
