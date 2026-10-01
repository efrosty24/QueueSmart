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

let services: Service[] = [
  {
    id: 'general',
    name: 'General Checkup',
    description: 'Routine checkups and general health concerns.',
    expectedDurationMinutes: 20,
    priority: 'medium',
    queueLength: 8,
    status: 'open',
  },
  {
    id: 'pharmacy',
    name: 'Pharmacy Pickup',
    description: 'Pick up prescriptions ordered by a clinician.',
    expectedDurationMinutes: 5,
    priority: 'low',
    queueLength: 3,
    status: 'open',
  },
  {
    id: 'lab',
    name: 'Lab Draw',
    description: 'Blood draws and specimen collection for lab tests.',
    expectedDurationMinutes: 10,
    priority: 'medium',
    queueLength: 0,
    status: 'closed',
  },
  {
    id: 'counseling',
    name: 'Counseling Walk-in',
    description: 'Same-day mental health support, no appointment needed.',
    expectedDurationMinutes: 30,
    priority: 'high',
    queueLength: 5,
    status: 'open',
  },
]

const simulateRequest = () => new Promise((resolve) => setTimeout(resolve, 400))

export async function fetchServices(): Promise<Service[]> {
  await simulateRequest()
  return services.map((service) => ({ ...service }))
}

export async function setQueueStatus(id: string, status: QueueStatus): Promise<Service> {
  await simulateRequest()
  services = services.map((service) => (service.id === id ? { ...service, status } : service))
  const updated = services.find((service) => service.id === id)
  if (!updated) throw new Error(`Unknown service: ${id}`)
  return { ...updated }
}

// New services start closed with an empty queue until an admin opens them.
export async function createService(input: ServiceInput): Promise<Service> {
  await simulateRequest()
  const service: Service = { id: crypto.randomUUID(), ...input, queueLength: 0, status: 'closed' }
  services = [...services, service]
  return { ...service }
}

export async function updateService(id: string, input: ServiceInput): Promise<Service> {
  await simulateRequest()
  services = services.map((service) => (service.id === id ? { ...service, ...input } : service))
  const updated = services.find((service) => service.id === id)
  if (!updated) throw new Error(`Unknown service: ${id}`)
  return { ...updated }
}

export async function deleteService(id: string): Promise<void> {
  await simulateRequest()
  if (!services.some((service) => service.id === id)) throw new Error(`Unknown service: ${id}`)
  services = services.filter((service) => service.id !== id)
}
