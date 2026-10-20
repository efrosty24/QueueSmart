// Client-side checks for fast feedback. They mirror backend/app/auth/validation.py,
// which re-validates everything; keep the two in sync.

export const PASSWORD_MIN_LENGTH = 8
// bcrypt on the server only uses 72 bytes, so passwords are capped well under that.
export const PASSWORD_MAX_LENGTH = 64
const EMAIL_MAX_LENGTH = 254
const EMAIL_LOCAL_MAX_LENGTH = 64

// Allowlist of characters found in normal addresses. Quotes, semicolons, equals
// signs, spaces, slashes and asterisks (what SQL injection needs) can't match.
const emailPattern =
  /^[a-z0-9._%+-]+@[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)*\.[a-z]{2,}$/
// Allowed characters that still mean something: "--" starts an SQL comment, ".." is never valid.
const forbiddenSequences = ['--', '..']
const uppercasePattern = /[A-Z]/
// Anything that isn't a letter, digit or whitespace: ! # $ % & * @ ...
const specialPattern = /[^A-Za-z0-9\s]/

export type FieldErrors<T extends string> = Partial<Record<T, string>>

export function validateEmail(email: string): string | undefined {
  const value = email.trim().toLowerCase()
  if (!value) return 'Email is required.'
  if (value.length > EMAIL_MAX_LENGTH || value.split('@')[0].length > EMAIL_LOCAL_MAX_LENGTH) {
    return 'Email is too long.'
  }
  if (!emailPattern.test(value) || forbiddenSequences.some((sequence) => value.includes(sequence))) {
    return 'Enter a valid email address, like name@university.edu.'
  }
}

// Login only checks presence and length; strength rules belong to registration.
export function validateLoginPassword(password: string): string | undefined {
  if (!password) return 'Password is required.'
  if (password.length > PASSWORD_MAX_LENGTH) return `Use at most ${PASSWORD_MAX_LENGTH} characters.`
}

export function validateNewPassword(password: string): string | undefined {
  if (!password) return 'Password is required.'
  if (password.length < PASSWORD_MIN_LENGTH) return `Use at least ${PASSWORD_MIN_LENGTH} characters.`
  if (password.length > PASSWORD_MAX_LENGTH || new TextEncoder().encode(password).length > 72) {
    return `Use at most ${PASSWORD_MAX_LENGTH} characters.`
  }
  if (!uppercasePattern.test(password)) return 'Include at least one uppercase letter.'
  if (!specialPattern.test(password)) return 'Include at least one special character, like ! or #.'
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
