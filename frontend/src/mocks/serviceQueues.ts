import type { ServiceId } from './services'

// Frontend-only availability. Replace with the clinic service/queue API later.
export const serviceQueues: Record<ServiceId, { description: string; waiting: number; open: boolean }> = {
  'sick-visit': { description: 'Meet with clinic staff about a new health concern.', waiting: 4, open: true },
  'flu-shot': { description: 'Visit the campus clinic for your seasonal flu vaccination.', waiting: 2, open: true },
  'prescription-refill': { description: 'Talk with clinic staff about an existing prescription.', waiting: 0, open: true },
  'lab-work': { description: 'Sample collection and testing requested by your clinic provider.', waiting: 0, open: false },
}
