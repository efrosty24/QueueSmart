import { useEffect, useState } from 'react'
import { SelectField } from '../../components/SelectField'
import { TextArea } from '../../components/TextArea'
import { TextField } from '../../components/TextField'
import { useForm } from '../../hooks/useForm'
import type { PriorityLevel, Service, ServiceInput } from './adminApi'
import {
  PRIORITY_OPTIONS,
  SERVICE_NAME_MAX_LENGTH,
  validateServiceForm,
  type ServiceField,
} from './serviceValidation'
import './admin.css'

type ServiceFormDialogProps = {
  service: Service | null // null = creating a new service
  onClose: () => void
  onSubmit: (input: ServiceInput) => Promise<void>
}

// Shared create/edit form for a service, shown as a modal over the service list.
export function ServiceFormDialog({ service, onClose, onSubmit }: ServiceFormDialogProps) {
  const [error, setError] = useState<string | null>(null)
  const isEditing = service !== null

  const { fieldProps, handleSubmit, submitting } = useForm<ServiceField>({
    initialValues: {
      name: service?.name ?? '',
      description: service?.description ?? '',
      durationMinutes: service ? String(service.expectedDurationMinutes) : '',
      priority: service?.priority ?? 'medium',
    },
    validate: validateServiceForm,
    onSubmit: async (values) => {
      setError(null)
      try {
        await onSubmit({
          name: values.name.trim(),
          description: values.description.trim(),
          expectedDurationMinutes: Number(values.durationMinutes),
          priority: values.priority as PriorityLevel,
        })
      } catch {
        setError(isEditing ? 'Could not save changes. Try again.' : 'Could not create the service. Try again.')
      }
    },
  })

  // Close on Escape.
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  return (
    <div
      className="dialog-scrim"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div className="dialog glass" role="dialog" aria-modal="true" aria-labelledby="service-form-title">
        <div className="dialog__heading">
          <h2 id="service-form-title">{isEditing ? 'Edit service' : 'Add service'}</h2>
          <button type="button" className="btn btn-ghost dialog__close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        <form className="service-form" onSubmit={handleSubmit} noValidate>
          {error && (
            <div className="alert alert-error" role="alert">
              {error}
            </div>
          )}
          <TextField
            label="Service name"
            maxLength={SERVICE_NAME_MAX_LENGTH}
            placeholder="e.g. General Checkup"
            autoFocus
            {...fieldProps('name')}
          />
          <TextArea
            label="Description"
            placeholder="What happens during this service?"
            rows={3}
            {...fieldProps('description')}
          />
          <TextField
            label="Expected duration (minutes)"
            type="number"
            inputMode="numeric"
            min={1}
            placeholder="e.g. 20"
            {...fieldProps('durationMinutes')}
          />
          <SelectField label="Priority level" options={PRIORITY_OPTIONS} {...fieldProps('priority')} />
          <div className="dialog__actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Saving…' : isEditing ? 'Save changes' : 'Add service'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
