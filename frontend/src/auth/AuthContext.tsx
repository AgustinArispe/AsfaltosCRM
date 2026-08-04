import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { currentUserRequest, loginRequest } from '../api/auth'
import { ApiError } from '../api/client'
import {
  readSessionToken,
  removeSessionToken,
  writeSessionToken,
} from './session-storage'
import type { AuthUser, LoginCredentials } from './types'

type AuthContextValue = {
  user: AuthUser | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (credentials: LoginCredentials) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const clearSession = useCallback(() => {
    removeSessionToken()
    setToken(null)
    setUser(null)
  }, [])

  useEffect(() => {
    const storedToken = readSessionToken()
    if (!storedToken) {
      setIsLoading(false)
      return
    }

    let isActive = true
    currentUserRequest(storedToken, clearSession)
      .then((currentUser) => {
        if (!isActive) return
        setToken(storedToken)
        setUser(currentUser)
      })
      .catch((error: unknown) => {
        if (!isActive) return
        if (error instanceof ApiError && error.status === 401) {
          clearSession()
        }
      })
      .finally(() => {
        if (isActive) setIsLoading(false)
      })

    return () => {
      isActive = false
    }
  }, [clearSession])

  const login = useCallback(
    async (credentials: LoginCredentials) => {
      const tokenResponse = await loginRequest(credentials)
      const accessToken = tokenResponse.access_token
      const currentUser = await currentUserRequest(accessToken, clearSession)

      writeSessionToken(accessToken)
      setToken(accessToken)
      setUser(currentUser)
    },
    [clearSession],
  )

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      isAuthenticated: Boolean(user && token),
      isLoading,
      login,
      logout: clearSession,
    }),
    [clearSession, isLoading, login, token, user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
