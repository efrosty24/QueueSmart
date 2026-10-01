import { useId, type TextareaHTMLAttributes } from 'react'
import './TextField.css'

type TextAreaProps = Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'id'> & {
  label: string
  error?: string
  hint?: string
}

// Multi-line sibling of TextField. Shares its styling and layout, so the two always match.
export function TextArea({ label, error, hint, ...textareaProps }: TextAreaProps) {
  const id = useId()
  const showHint = Boolean(hint) && !error
  const describedBy = [showHint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(' ')

  return (
    <div className="field">
      <label htmlFor={id} className="field__label">
        {label}
      </label>
      <div className="field__control">
        <textarea
          id={id}
          className="field__input field__input--textarea"
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy || undefined}
          {...textareaProps}
        />
      </div>
      {showHint && (
        <p id={`${id}-hint`} className="field__hint">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="field__error" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
