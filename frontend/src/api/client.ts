const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim() || '/api'
const API_BASE_URL = configuredBaseUrl.replace(/\/$/, '')

type ApiRequestOptions = Omit<RequestInit, 'body' | 'headers'> & {
  body?: unknown
  token?: string | null
  onUnauthorized?: () => void
}

type ErrorPayload = {
  detail?: string
}

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function readJson(response: Response): Promise<unknown> {
  const content = await response.text()
  return content ? (JSON.parse(content) as unknown) : null
}

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const { body, token, onUnauthorized, ...requestOptions } = options
  const headers = new Headers({ Accept: 'application/json' })

  if (body !== undefined) {
    headers.set('Content-Type', 'application/json')
  }
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...requestOptions,
    body: body === undefined ? undefined : JSON.stringify(body),
    headers,
  })
  const payload = await readJson(response)

  if (!response.ok) {
    if (response.status === 401) {
      onUnauthorized?.()
    }
    const detail = (payload as ErrorPayload | null)?.detail
    throw new ApiError(response.status, detail || 'Request failed')
  }

  return payload as T
}
