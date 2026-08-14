import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react'

import { getActiveNotificationTotal } from '../api/notifications'
import type { ApiSession } from '../api/opportunities'

export const NOTIFICATION_REFRESH_INTERVAL_MS = 60_000

type AttentionState = {
  count: number
  refresh: () => void
}

const NotificationAttentionContext = createContext<AttentionState | null>(null)

function canRefreshNotifications(): boolean {
  return document.visibilityState === 'visible' && navigator.onLine
}

export function useNotificationAttention(session: ApiSession): AttentionState {
  const [count, setCount] = useState(0)
  const requestRef = useRef<AbortController | null>(null)
  const refresh = useCallback(() => {
    if (!canRefreshNotifications() || requestRef.current) return
    const controller = new AbortController()
    requestRef.current = controller
    getActiveNotificationTotal({ ...session, signal: controller.signal })
      .then((response) => {
        if (!controller.signal.aborted) setCount(response.total)
      })
      .catch(() => {
        // Attention remains at its last authoritative value until a later successful refresh.
      })
      .finally(() => {
        if (requestRef.current === controller) requestRef.current = null
      })
  }, [session])

  useEffect(() => {
    refresh()
    const interval = window.setInterval(refresh, NOTIFICATION_REFRESH_INTERVAL_MS)
    const refreshOnRecovery = () => refresh()
    window.addEventListener('focus', refreshOnRecovery)
    window.addEventListener('online', refreshOnRecovery)
    document.addEventListener('visibilitychange', refreshOnRecovery)
    window.addEventListener('faa-notification-attention-refresh', refreshOnRecovery)
    return () => {
      window.clearInterval(interval)
      requestRef.current?.abort()
      requestRef.current = null
      window.removeEventListener('focus', refreshOnRecovery)
      window.removeEventListener('online', refreshOnRecovery)
      document.removeEventListener('visibilitychange', refreshOnRecovery)
      window.removeEventListener('faa-notification-attention-refresh', refreshOnRecovery)
    }
  }, [refresh])

  return { count, refresh }
}

export function NotificationAttentionProvider({
  children,
  value,
}: {
  children: ReactNode
  value: AttentionState
}) {
  return (
    <NotificationAttentionContext.Provider value={value}>
      {children}
    </NotificationAttentionContext.Provider>
  )
}

export function NotificationAttentionBoundary({
  children,
  session,
}: {
  children: ReactNode
  session: ApiSession
}) {
  const attention = useNotificationAttention(session)
  return <NotificationAttentionProvider value={attention}>{children}</NotificationAttentionProvider>
}

export function useNotificationAttentionContext(): AttentionState | null {
  return useContext(NotificationAttentionContext)
}

export function refreshNotificationAttention(): void {
  window.dispatchEvent(new Event('faa-notification-attention-refresh'))
}
