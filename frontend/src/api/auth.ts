import { apiRequest } from './client'
import type { AuthUser, LoginCredentials, TokenResponse } from '../auth/types'

export function loginRequest(credentials: LoginCredentials) {
  return apiRequest<TokenResponse>('/auth/login', {
    method: 'POST',
    body: credentials,
  })
}

export function currentUserRequest(token: string, onUnauthorized?: () => void) {
  return apiRequest<AuthUser>('/auth/me', {
    token,
    onUnauthorized,
  })
}
