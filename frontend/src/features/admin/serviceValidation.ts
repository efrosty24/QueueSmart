// Client-side checks only, for fast feedback. The FastAPI backend will have to re-validate everything.
import type { PriorityLevel } from './adminApi'

export type FieldErrors<T extends string> = Partial<Record<T, string>>

export const SERVICE_NAME_MAX_LENGTH = 100
export const MIN_DURATION_MINUTES = 1
export const MAX_DURATION_MINUTES = 480 // 8 hours; a generous ceiling for a single service

export const PRIORITY_OPTIONS: { value: PriorityLevel; label: string }[] = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
]

export function validateServiceName(name: string): string | undefined {
  const value = name.trim()
  if (!value) return 'Service name is required.'
  if (value.length > SERVICE_NAME_MAX_LENGTH) return `Use at most ${SERVICE_NAME_MAX_LENGTH} characters.`
}

export function validateServiceDescription(description: string): string | undefined {
  if (!description.trim()) return 'Description is required.'
}

export function validateDurationMinutes(durationMinutes: string): string | undefined {
  const value = durationMinutes.trim()
  if (!value) return 'Expected duration is required.'
  if (!/^\d+$/.test(value)) return 'Enter a whole number of minutes.'
  const parsed = Number(value)
  if (parsed < MIN_DURATION_MINUTES) return `Use at least ${MIN_DURATION_MINUTES} minute.`
  if (parsed > MAX_DURATION_MINUTES) return `Use at most ${MAX_DURATION_MINUTES} minutes.`
}

export function validatePriority(priority: string): string | undefined {
  if (!PRIORITY_OPTIONS.some((option) => option.value === priority)) return 'Choose a priority level.'
}

export type ServiceField = 'name' | 'description' | 'durationMinutes' | 'priority'
export type ServiceFormValues = Record<ServiceField, string>

export function validateServiceForm(values: ServiceFormValues): FieldErrors<ServiceField> {
  return {
    name: validateServiceName(values.name),
    description: validateServiceDescription(values.description),
    durationMinutes: validateDurationMinutes(values.durationMinutes),
    priority: validatePriority(values.priority),
  }
}
