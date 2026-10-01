import type { SessionUser } from './session'

// Placeholder auth calls. There is no backend yet; requests are simulated.
// Login recognizes admin@university.edu as a mock administrator.
// All other logins and all registrations create patient sessions.
// TODO: replace with real calls to the FastAPI auth endpoints.

export type Credentials = {
  email: string
  password: string
}

const simulateRequest = () => new Promise((resolve) => setTimeout(resolve, 600))

export async function login(credentials: Credentials): Promise<SessionUser> {
  await simulateRequest()

  const email = credentials.email.trim().toLowerCase()

  return {
    email,
    role: email === 'admin@university.edu' ? 'admin' : 'patient',
  }
}

export async function register(credentials: Credentials): Promise<SessionUser> {
  await simulateRequest()
  return { email: credentials.email.trim().toLowerCase(), role: 'patient' }
}
