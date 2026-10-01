import { useEffect, useId, useRef, type ReactNode } from 'react'
import './ConfirmDialog.css'

type ConfirmDialogProps = {
  open: boolean
  title: string
  message: ReactNode
  confirmLabel: string
  cancelLabel?: string
  icon?: ReactNode
  tone?: 'danger' | 'primary'
  pending?: boolean
  onConfirm: () => void
  onCancel: () => void
}

// Small modal popup for "are you sure?" moments. Uses the native <dialog>,
// which traps focus, closes on Escape and returns focus to the trigger.
export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel,
  cancelLabel = 'Cancel',
  icon,
  tone = 'primary',
  pending = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  const messageId = useId()

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  return (
    <dialog
      ref={dialogRef}
      className="confirm-dialog glass"
      aria-labelledby={titleId}
      aria-describedby={messageId}
      onCancel={(event) => {
        // Escape key: let React state close it so `open` stays in sync.
        event.preventDefault()
        if (!pending) onCancel()
      }}
      onClick={(event) => {
        // A click on the dialog element itself means the backdrop was clicked.
        if (event.target === dialogRef.current && !pending) onCancel()
      }}
    >
      <div className="confirm-dialog__body">
        {icon && <div className={`confirm-dialog__icon confirm-dialog__icon--${tone}`}>{icon}</div>}
        <h2 id={titleId}>{title}</h2>
        <p id={messageId}>{message}</p>
        <div className="confirm-dialog__actions">
          <button type="button" className="btn btn-ghost btn-pill" onClick={onCancel} disabled={pending} autoFocus>
            {cancelLabel}
          </button>
          <button
            type="button"
            className={`btn btn-pill ${tone === 'danger' ? 'btn-danger' : 'btn-primary'}`}
            onClick={onConfirm}
            disabled={pending}
          >
            {pending ? 'Working…' : confirmLabel}
          </button>
        </div>
      </div>
    </dialog>
  )
}
