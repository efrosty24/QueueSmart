// Client-side checks only, for fast feedback. The FastAPI backend must re-validate everything.

export const PASSWORD_MIN_LENGTH = 8
export const PASSWORD_MAX_LENGTH = 128

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export type FieldErrors<T extends string> = Partial<Record<T, string>>

export function validateEmail(email: string): string | undefined {
  const value = email.trim()
  if (!value) return 'Email is required.'
  if (!emailPattern.test(value)) return 'Enter a valid email address, like name@university.edu.'
}

// Login only checks presence; strength rules belong to registration.
export function validateLoginPassword(password: string): string | undefined {
  if (!password) return 'Password is required.'
}

export function validateNewPassword(password: string): string | undefined {
  if (!password) return 'Password is required.'
  if (password.length < PASSWORD_MIN_LENGTH) return `Use at least ${PASSWORD_MIN_LENGTH} characters.`
  if (password.length > PASSWORD_MAX_LENGTH) return `Use at most ${PASSWORD_MAX_LENGTH} characters.`
  if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) return 'Include at least one letter and one number.'
}

export function validateConfirmPassword(password: string, confirm: string): string | undefined {
  if (!confirm) return 'Confirm your password.'
  if (confirm !== password) return 'Passwords do not match.'
}

export type LoginField = 'email' | 'password'
export type LoginValues = Record<LoginField, string>

export function validateLogin(values: LoginValues): FieldErrors<LoginField> {
  return {
    email: validateEmail(values.email),
    password: validateLoginPassword(values.password),
  }
}

export type RegisterField = 'email' | 'password' | 'confirmPassword'
export type RegisterValues = Record<RegisterField, string>

export function validateRegister(values: RegisterValues): FieldErrors<RegisterField> {
  return {
    email: validateEmail(values.email),
    password: validateNewPassword(values.password),
    confirmPassword: validateConfirmPassword(values.password, values.confirmPassword),
  }
}

export function hasErrors(errors: FieldErrors<string>) {
  return Object.values(errors).some(Boolean)
}
