// Small fetch wrapper for the FastAPI backend. Requests go to /api/..., which the
// Vite dev server (and nginx in Docker) forwards to the backend.

export class ApiError extends Error {
  readonly status: number
  // Per-field messages from a 422 validation error, e.g. { email: 'Email is required.' }.
  readonly fieldErrors: Record<string, string>

  constructor(status: number, message: string, fieldErrors: Record<string, string> = {}) {
    super(message)
    this.status = status
    this.fieldErrors = fieldErrors
  }
}

type RequestOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  token?: string | null
}

export async function apiRequest<T>(path: string, { method = 'GET', body, token }: RequestOptions = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api${path}`, {
      method,
      headers: {
        ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, "Can't reach the QueueSmart server. Check that the backend is running.")
  }

  if (response.status === 204) return undefined as T

  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = typeof data?.detail === 'string' ? data.detail : 'Something went wrong. Please try again.'
    throw new ApiError(response.status, detail, data?.errors ?? {})
  }
  return data as T
}

// One line to show the user: field messages for validation errors, otherwise the server's detail.
export function errorMessage(error: unknown, fallback: string) {
  if (!(error instanceof ApiError)) return fallback
  const fieldMessages = Object.values(error.fieldErrors)
  return fieldMessages.length ? fieldMessages.join(' ') : error.message
}
