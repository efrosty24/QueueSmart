import { useId, type SelectHTMLAttributes } from 'react'
import './TextField.css'

type SelectOption = { value: string; label: string }

type SelectFieldProps = Omit<SelectHTMLAttributes<HTMLSelectElement>, 'id'> & {
  label: string
  options: SelectOption[]
  error?: string
  hint?: string
}

// Dropdown sibling of TextField, for a fixed set of choices. Shares its styling and layout.
export function SelectField({ label, options, error, hint, ...selectProps }: SelectFieldProps) {
  const id = useId()
  const showHint = Boolean(hint) && !error
  const describedBy = [showHint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(' ')

  return (
    <div className="field">
      <label htmlFor={id} className="field__label">
        {label}
      </label>
      <div className="field__control">
        <select
          id={id}
          className="field__input"
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy || undefined}
          {...selectProps}
        >
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
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
