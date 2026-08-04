export type UserRole = 'SUPERVISOR' | 'VENDEDOR'

export type AuthUser = {
  id: number
  full_name: string
  email: string
  role: UserRole
  is_active: boolean
  created_at: string
  updated_at: string
}

export type LoginCredentials = {
  email: string
  password: string
}

export type TokenResponse = {
  access_token: string
  token_type: 'bearer'
  expires_in: number
}
