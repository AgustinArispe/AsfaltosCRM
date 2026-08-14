import { useCallback, useEffect, useRef, useState } from 'react'

import {
  listNotifications,
  type NotificationView,
  type OperationalNotification,
} from '../api/notifications'
import type { ApiSession } from '../api/opportunities'
import { NOTIFICATION_REFRESH_INTERVAL_MS } from './NotificationAttention'

type NotificationListState = {
  error: 'initial' | 'background' | null
  hasLoaded: boolean
  isLoadingMore: boolean
  isRefreshing: boolean
  items: OperationalNotification[]
  loadMore: () => void
  pendingFirstPage: OperationalNotification[] | null
  refresh: () => void
  total: number
  applyPendingFirstPage: () => void
  replaceNotification: (notification: OperationalNotification) => void
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}

function sortNotifications(items: OperationalNotification[]): OperationalNotification[] {
  return [...items].sort((left, right) => {
    const createdAtDifference = Date.parse(right.created_at) - Date.parse(left.created_at)
    return createdAtDifference || right.id - left.id
  })
}

function mergeNotifications(
  current: OperationalNotification[],
  incoming: OperationalNotification[],
): OperationalNotification[] {
  const byId = new Map(current.map((notification) => [notification.id, notification]))
  incoming.forEach((notification) => {
    byId.set(notification.id, notification)
  })
  return sortNotifications([...byId.values()])
}

function canRefreshNotifications(): boolean {
  return document.visibilityState === 'visible' && navigator.onLine
}

export function useNotifications(
  view: NotificationView,
  session: ApiSession,
): NotificationListState {
  const [items, setItems] = useState<OperationalNotification[]>([])
  const [total, setTotal] = useState(0)
  const [hasLoaded, setHasLoaded] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [error, setError] = useState<'initial' | 'background' | null>(null)
  const [pendingFirstPage, setPendingFirstPage] = useState<OperationalNotification[] | null>(null)
  const requestRef = useRef<AbortController | null>(null)
  const hasLoadedRef = useRef(false)
  const pageRef = useRef(1)
  const itemsRef = useRef<OperationalNotification[]>([])

  useEffect(() => {
    itemsRef.current = items
  }, [items])

  const loadFirstPage = useCallback(
    (fromPolling = false) => {
      if (requestRef.current || (fromPolling && !canRefreshNotifications())) return
      const controller = new AbortController()
      requestRef.current = controller
      setIsRefreshing(hasLoadedRef.current)
      listNotifications({ page: 1, view }, { ...session, signal: controller.signal })
        .then((response) => {
          if (controller.signal.aborted) return
          pageRef.current = 1
          setTotal(response.total)
          setError(null)
          if (hasLoadedRef.current && window.scrollY > 16) {
            setPendingFirstPage(response.items)
          } else {
            setItems((current) => mergeNotifications(current, response.items))
            setPendingFirstPage(null)
          }
          hasLoadedRef.current = true
          setHasLoaded(true)
        })
        .catch((value: unknown) => {
          if (!isAbortError(value)) setError(hasLoadedRef.current ? 'background' : 'initial')
        })
        .finally(() => {
          if (requestRef.current === controller) requestRef.current = null
          if (!controller.signal.aborted) setIsRefreshing(false)
        })
    },
    [session, view],
  )

  useEffect(() => {
    requestRef.current?.abort()
    requestRef.current = null
    hasLoadedRef.current = false
    pageRef.current = 1
    setItems([])
    setTotal(0)
    setHasLoaded(false)
    setError(null)
    setPendingFirstPage(null)
    loadFirstPage()
    return () => requestRef.current?.abort()
  }, [loadFirstPage])

  useEffect(() => {
    const interval = window.setInterval(() => loadFirstPage(true), NOTIFICATION_REFRESH_INTERVAL_MS)
    const refreshOnRecovery = () => loadFirstPage(true)
    window.addEventListener('focus', refreshOnRecovery)
    window.addEventListener('online', refreshOnRecovery)
    document.addEventListener('visibilitychange', refreshOnRecovery)
    return () => {
      window.clearInterval(interval)
      window.removeEventListener('focus', refreshOnRecovery)
      window.removeEventListener('online', refreshOnRecovery)
      document.removeEventListener('visibilitychange', refreshOnRecovery)
    }
  }, [loadFirstPage])

  const loadMore = useCallback(() => {
    if (requestRef.current || itemsRef.current.length >= total) return
    const controller = new AbortController()
    requestRef.current = controller
    setIsLoadingMore(true)
    const nextPage = pageRef.current + 1
    listNotifications({ page: nextPage, view }, { ...session, signal: controller.signal })
      .then((response) => {
        if (controller.signal.aborted) return
        pageRef.current = nextPage
        setTotal(response.total)
        setItems((current) => mergeNotifications(current, response.items))
        setError(null)
      })
      .catch((value: unknown) => {
        if (!isAbortError(value)) setError('background')
      })
      .finally(() => {
        if (requestRef.current === controller) requestRef.current = null
        if (!controller.signal.aborted) setIsLoadingMore(false)
      })
  }, [session, total, view])

  const applyPendingFirstPage = useCallback(() => {
    if (!pendingFirstPage) return
    setItems((current) => mergeNotifications(current, pendingFirstPage))
    setPendingFirstPage(null)
  }, [pendingFirstPage])

  const replaceNotification = useCallback((notification: OperationalNotification) => {
    setItems((current) => mergeNotifications(current, [notification]))
  }, [])

  return {
    applyPendingFirstPage,
    error,
    hasLoaded,
    isLoadingMore,
    isRefreshing,
    items,
    loadMore,
    pendingFirstPage,
    refresh: () => loadFirstPage(),
    replaceNotification,
    total,
  }
}
