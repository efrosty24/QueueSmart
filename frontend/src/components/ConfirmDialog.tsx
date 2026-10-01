import { useEffect, useId } from 'react'

type ConfirmDialogProps = {
  title: string
  message: string
  confirmLabel: string
  cancelLabel?: string
  pending?: boolean
  onConfirm: () => void
  onCancel: () => void
}

// Generic "are you sure?" dialog for destructive actions. Reuses the shared
// .dialog classes from global.css, so it matches ServiceFormDialog and others.
export function ConfirmDialog({
  title,
  message,
  confirmLabel,
  cancelLabel = 'Cancel',
  pending = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const titleId = useId()
  const messageId = useId()

  // Close on Escape as a convenience; this isn't a full focus trap.
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onCancel()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onCancel])

  return (
    <div
      className="dialog-scrim"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onCancel()
      }}
    >
      <div className="dialog glass" role="alertdialog" aria-modal="true" aria-labelledby={titleId} aria-describedby={messageId}>
        <div className="dialog__heading">
          <h2 id={titleId}>{title}</h2>
          <button type="button" className="btn btn-ghost dialog__close" onClick={onCancel} aria-label="Close">
            ✕
          </button>
        </div>
        <p id={messageId} className="dialog__message">
          {message}
        </p>
        <div className="dialog__actions">
          <button type="button" className="btn btn-ghost" onClick={onCancel} disabled={pending}>
            {cancelLabel}
          </button>
          <button type="button" className="btn btn-danger" onClick={onConfirm} disabled={pending}>
            {pending ? 'Working…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
