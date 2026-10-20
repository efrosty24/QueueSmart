import { apiRequest } from '../../lib/api'
import type { SessionUser, StoredSession } from './session'

// Calls to the FastAPI auth module (backend/app/auth/router.py).
// The server decides the role: emails whose name part contains "admin" are administrators.

export type Credentials = {
  email: string
  password: string
}

type AuthResponse = {
  token: string
  expires_at: string
  user: SessionUser
}

function toSession({ token, expires_at, user }: AuthResponse): StoredSession {
  return { token, expiresAt: expires_at, user }
}

export async function login(credentials: Credentials): Promise<StoredSession> {
  return toSession(await apiRequest<AuthResponse>('/auth/login', { method: 'POST', body: credentials }))
}

export async function register(credentials: Credentials): Promise<StoredSession> {
  return toSession(await apiRequest<AuthResponse>('/auth/register', { method: 'POST', body: credentials }))
}

export function fetchCurrentUser(token: string): Promise<SessionUser> {
  return apiRequest<SessionUser>('/auth/me', { token })
}

export function logout(token: string): Promise<void> {
  return apiRequest<void>('/auth/logout', { method: 'POST', token })
}
