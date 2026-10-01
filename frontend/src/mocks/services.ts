// Mock clinic services, matching the A1 design. Replace with GET /services once the backend exists.

export type ServiceId = 'sick-visit' | 'flu-shot' | 'prescription-refill' | 'lab-work'

export type Service = {
  id: ServiceId
  name: string
  // Expected minutes per patient; used for wait estimates.
  expectedMinutes: number
  priority: 'low' | 'medium' | 'high'
}

export const services: Record<ServiceId, Service> = {
  'sick-visit': { id: 'sick-visit', name: 'Sick Visit', expectedMinutes: 12, priority: 'high' },
  'flu-shot': { id: 'flu-shot', name: 'Flu Shot', expectedMinutes: 5, priority: 'low' },
  'prescription-refill': {
    id: 'prescription-refill',
    name: 'Prescription Refill',
    expectedMinutes: 6,
    priority: 'medium',
  },
  'lab-work': { id: 'lab-work', name: 'Lab Work', expectedMinutes: 10, priority: 'medium' },
}
