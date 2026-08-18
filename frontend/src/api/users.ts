import type { AuthUser, UserRole } from '../auth/types'
import { apiRequest } from './client'
import type { ApiSession } from './opportunities'

export type UserCreatePayload = {
  full_name: string
  email: string
  password: string
  role: UserRole
}

export type UserUpdatePayload = Partial<
  Pick<AuthUser, 'full_name' | 'email' | 'role' | 'is_active'>
>

export function listUsers(session: ApiSession) {
  return apiRequest<AuthUser[]>('/users', session)
}

export function createUser(payload: UserCreatePayload, session: ApiSession) {
  return apiRequest<AuthUser>('/users', { ...session, method: 'POST', body: payload })
}

export function updateUser(userId: number, payload: UserUpdatePayload, session: ApiSession) {
  return apiRequest<AuthUser>(`/users/${userId}`, { ...session, method: 'PATCH', body: payload })
}

export function replaceUserPassword(userId: number, password: string, session: ApiSession) {
  return apiRequest<AuthUser>(`/users/${userId}/password`, {
    ...session,
    method: 'PUT',
    body: { password },
  })
}
