import type { SessionUser } from './session'

// Placeholder auth calls. There is no backend yet, so these only simulate a request
// and always succeed. Every account is a patient for now.
// TODO: replace with real calls to the FastAPI auth endpoints once the backend exists.

export type Credentials = {
  email: string
  password: string
}

const simulateRequest = () => new Promise((resolve) => setTimeout(resolve, 600))

export async function login(credentials: Credentials): Promise<SessionUser> {
  await simulateRequest()
  return { email: credentials.email.trim().toLowerCase(), role: 'patient' }
}

export async function register(credentials: Credentials): Promise<SessionUser> {
  await simulateRequest()
  return { email: credentials.email.trim().toLowerCase(), role: 'patient' }
}
