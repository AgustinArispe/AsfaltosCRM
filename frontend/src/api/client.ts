const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim() || '/api'
const API_BASE_URL = configuredBaseUrl.replace(/\/$/, '')

type ApiRequestOptions = Omit<RequestInit, 'body' | 'headers'> & {
  body?: unknown
  token?: string | null
  onUnauthorized?: () => void
}

type ApiBinaryRequestOptions = Omit<RequestInit, 'body' | 'headers'> & {
  body?: BodyInit
  token?: string | null
  onUnauthorized?: () => void
}

export type ApiErrorDetail =
  | string
  | { code?: string; resource?: string; current_updated_at?: string }

type ErrorPayload = { detail?: ApiErrorDetail }

export class ApiError extends Error {
  readonly status: number
  readonly detail: ApiErrorDetail | undefined

  constructor(status: number, message: string, detail?: ApiErrorDetail) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

async function readJson(response: Response): Promise<unknown> {
  const content = await response.text()
  return content ? (JSON.parse(content) as unknown) : null
}

function requestHeaders(token: string | null | undefined): Headers {
  const headers = new Headers({ Accept: 'application/json' })
  if (token) headers.set('Authorization', `Bearer ${token}`)
  return headers
}

async function throwApiError(
  response: Response,
  onUnauthorized: (() => void) | undefined,
): Promise<never> {
  if (response.status === 401) onUnauthorized?.()
  const payload = await readJson(response)
  const detail = (payload as ErrorPayload | null)?.detail
  throw new ApiError(
    response.status,
    typeof detail === 'string' ? detail : 'Request failed',
    detail,
  )
}

export function isStaleWriteConflict(error: unknown): error is ApiError {
  return (
    error instanceof ApiError &&
    error.status === 409 &&
    typeof error.detail === 'object' &&
    error.detail?.code === 'STALE_WRITE'
  )
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { body, token, onUnauthorized, ...requestOptions } = options
  const headers = requestHeaders(token)

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
  if (!response.ok) {
    return throwApiError(response, onUnauthorized)
  }

  const payload = await readJson(response)
  return payload as T
}

export async function apiFormRequest<T>(
  path: string,
  formData: FormData,
  options: ApiBinaryRequestOptions = {},
): Promise<T> {
  const { token, onUnauthorized, ...requestOptions } = options
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...requestOptions,
    body: formData,
    headers: requestHeaders(token),
  })
  if (!response.ok) return throwApiError(response, onUnauthorized)
  return (await readJson(response)) as T
}

export async function apiBlobRequest(
  applicationPath: string,
  options: ApiBinaryRequestOptions = {},
): Promise<Blob> {
  if (!applicationPath.startsWith('/api/whatsapp/')) {
    throw new ApiError(422, 'Invalid media path')
  }
  const { token, onUnauthorized, ...requestOptions } = options
  const response = await fetch(applicationPath, {
    ...requestOptions,
    headers: requestHeaders(token),
  })
  if (!response.ok) return throwApiError(response, onUnauthorized)
  return response.blob()
}
