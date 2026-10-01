import { useEffect, useId, useRef, useState } from 'react'
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
// Uses the native <dialog>, same as ConfirmDialog, for a bigger form instead of a yes/no choice.
export function ServiceFormDialog({ service, onClose, onSubmit }: ServiceFormDialogProps) {
  const [error, setError] = useState<string | null>(null)
  const dialogRef = useRef<HTMLDialogElement>(null)
  const titleId = useId()
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

  // This component is only ever mounted while the dialog should be open.
  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    dialog.showModal()
    return () => dialog.close()
  }, [])

  return (
    <dialog
      ref={dialogRef}
      className="service-form-dialog glass"
      aria-labelledby={titleId}
      onCancel={(event) => {
        // Escape key: let React state close it instead of the dialog closing itself.
        event.preventDefault()
        onClose()
      }}
      onClick={(event) => {
        // A click on the dialog element itself means the backdrop was clicked.
        if (event.target === dialogRef.current) onClose()
      }}
    >
      <div className="service-form-dialog__body">
        <div className="service-form-dialog__heading">
          <h2 id={titleId}>{isEditing ? 'Edit service' : 'Add service'}</h2>
          <button
            type="button"
            className="btn btn-ghost service-form-dialog__close"
            onClick={onClose}
            aria-label="Close"
          >
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
          <div className="service-form-dialog__actions">
            <button type="button" className="btn btn-ghost btn-pill" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary btn-pill" disabled={submitting}>
              {submitting ? 'Saving…' : isEditing ? 'Save changes' : 'Add service'}
            </button>
          </div>
        </form>
      </div>
    </dialog>
  )
}
