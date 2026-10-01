import { useState, type ChangeEvent, type FormEvent } from 'react'

type FieldErrors<F extends string> = Partial<Record<F, string>>

type FieldChangeEvent = ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>

type Options<F extends string> = {
  initialValues: Record<F, string>
  validate: (values: Record<F, string>) => FieldErrors<F>
  onSubmit: (values: Record<F, string>) => Promise<void>
}

// Shared form state for text-based forms (inputs, textareas and selects): errors show
// after a field is blurred or after the first submit attempt, then update live as the
// user types.
export function useForm<F extends string>({ initialValues, validate, onSubmit }: Options<F>) {
  const [values, setValues] = useState(initialValues)
  const [touched, setTouched] = useState<Partial<Record<F, boolean>>>({})
  const [submitAttempted, setSubmitAttempted] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const errors = validate(values)
  const visibleError = (field: F) => (touched[field] || submitAttempted ? errors[field] : undefined)

  const fieldProps = (field: F) => ({
    name: field,
    value: values[field],
    error: visibleError(field),
    onChange: (event: FieldChangeEvent) => setValues((current) => ({ ...current, [field]: event.target.value })),
    onBlur: () => setTouched((current) => ({ ...current, [field]: true })),
  })

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSubmitAttempted(true)
    if (Object.values(errors).some(Boolean)) {
      // Move focus to the first invalid field so keyboard and screen reader users land on it.
      const firstInvalid = (Object.keys(values) as F[]).find((field) => errors[field])
      if (firstInvalid) event.currentTarget.querySelector<HTMLElement>(`[name="${firstInvalid}"]`)?.focus()
      return
    }
    setSubmitting(true)
    try {
      await onSubmit(values)
    } finally {
      setSubmitting(false)
    }
  }

  return { fieldProps, handleSubmit, submitting }
}
