import { useCallback, useEffect, useRef, useState } from 'react'

import { ApiError } from '../api/client'
import {
  getMetricsOverview,
  getPipelineMetrics,
  getProductMetrics,
  getProvinceMetrics,
  getSourceMetrics,
  getTimelineMetrics,
} from '../api/metrics'
import { getNotificationTotal } from '../api/notifications'
import type { ApiSession } from '../api/opportunities'
import { listProducts } from '../api/products'
import { getWhatsAppAttentionSummary } from '../api/whatsapp'
import type { Product } from '../products/types'
import type { DashboardFilters } from './filters'
import { pipelineDimensions, timelineGranularity } from './filters'
import type { DashboardData } from './types'

export type DashboardAttention = {
  staleTotal: number | null
  waitingTotal: number | null
  oldestWaitingSinceAt: string | null
}

type DashboardErrors = Partial<Record<keyof DashboardData | 'attention', string>>

function dashboardErrorMessage(error: unknown): string {
  if (error instanceof ApiError && typeof error.detail === 'object') {
    if (error.detail?.code === 'METRICS_TIMELINE_PERIOD_TOO_LARGE') {
      return 'El período es demasiado amplio para esta granularidad. Elegí un rango más corto.'
    }
  }
  return 'No pudimos actualizar esta información. Conservamos los últimos datos disponibles.'
}

function commercialValue(
  key: 'overview' | 'products' | 'sources' | 'provinces' | 'timeline',
  value: unknown,
): unknown {
  if (key === 'products' || key === 'sources' || key === 'provinces') {
    return (value as { items: unknown[] }).items
  }
  return value
}

export function useDashboardMetrics(
  filters: DashboardFilters,
  session: ApiSession,
  _unreadTotal: number | null,
) {
  const [data, setData] = useState<Partial<DashboardData>>({})
  const [attention, setAttention] = useState<DashboardAttention>({
    staleTotal: null,
    waitingTotal: null,
    oldestWaitingSinceAt: null,
  })
  const [products, setProducts] = useState<Product[]>([])
  const [errors, setErrors] = useState<DashboardErrors>({})
  const [hasLoaded, setHasLoaded] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const commercialVersion = useRef(0)
  const pipelineVersion = useRef(0)
  const hasLoadedRef = useRef(false)
  const attentionFailuresRef = useRef({ stale: false, waiting: false })
  const retry = useCallback(() => setRefreshKey((value) => value + 1), [])
  const setAttentionFailure = useCallback((resource: 'stale' | 'waiting', failed: boolean) => {
    attentionFailuresRef.current[resource] = failed
    setErrors((current) => {
      const next = { ...current }
      if (attentionFailuresRef.current.stale || attentionFailuresRef.current.waiting) {
        next.attention = 'unavailable'
      } else {
        delete next.attention
      }
      return next
    })
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    listProducts(true, { ...session, signal: controller.signal })
      .then((items) => {
        if (!controller.signal.aborted) setProducts(items)
      })
      .catch(() => {
        if (!controller.signal.aborted)
          setErrors((current) => ({ ...current, products: 'unavailable' }))
      })
    return () => controller.abort()
  }, [session])

  useEffect(() => {
    void refreshKey
    const controller = new AbortController()
    const version = commercialVersion.current + 1
    commercialVersion.current = version
    setIsRefreshing(hasLoadedRef.current)
    const requestSession = { ...session, signal: controller.signal }
    void Promise.allSettled([
      getMetricsOverview(filters, requestSession),
      getProductMetrics(filters, requestSession),
      getSourceMetrics(filters, requestSession),
      getProvinceMetrics(filters, requestSession),
      getTimelineMetrics(filters, timelineGranularity(filters), requestSession),
    ]).then((results) => {
      if (controller.signal.aborted || commercialVersion.current !== version) return
      const keys = ['overview', 'products', 'sources', 'provinces', 'timeline'] as const
      const nextData: Partial<DashboardData> = {}
      const nextErrors: DashboardErrors = {}
      results.forEach((result, index) => {
        const key = keys[index]
        if (!key) return
        if (result.status === 'fulfilled') {
          Object.assign(nextData, { [key]: commercialValue(key, result.value) })
        } else {
          nextErrors[key] = dashboardErrorMessage(result.reason)
        }
      })
      setData((current) => ({ ...current, ...nextData }))
      setErrors((current) => {
        const next = { ...current }
        for (const key of keys) delete next[key]
        return { ...next, ...nextErrors }
      })
      hasLoadedRef.current = true
      setHasLoaded(true)
      setIsRefreshing(false)
    })
    return () => controller.abort()
  }, [filters, refreshKey, session])

  const { productId, province, source } = pipelineDimensions(filters)
  useEffect(() => {
    void refreshKey
    const controller = new AbortController()
    const version = pipelineVersion.current + 1
    pipelineVersion.current = version
    getPipelineMetrics({ productId, province, source }, { ...session, signal: controller.signal })
      .then((pipeline) => {
        if (controller.signal.aborted || pipelineVersion.current !== version) return
        setData((current) => ({ ...current, pipeline }))
        setErrors((current) => {
          const next = { ...current }
          delete next.pipeline
          return next
        })
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted)
          setErrors((current) => ({ ...current, pipeline: dashboardErrorMessage(error) }))
      })
    return () => controller.abort()
  }, [productId, province, source, refreshKey, session])

  useEffect(() => {
    void refreshKey
    const controller = new AbortController()
    getNotificationTotal(false, { ...session, signal: controller.signal }, 'OPPORTUNITY_STALE')
      .then((result) => {
        if (!controller.signal.aborted) {
          setAttention((current) => ({ ...current, staleTotal: result.total }))
          setAttentionFailure('stale', false)
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) setAttentionFailure('stale', true)
      })
    return () => controller.abort()
  }, [refreshKey, session, setAttentionFailure])

  useEffect(() => {
    void refreshKey
    const controller = new AbortController()
    getWhatsAppAttentionSummary({ ...session, signal: controller.signal })
      .then((result) => {
        if (!controller.signal.aborted) {
          setAttention((current) => ({
            ...current,
            waitingTotal: result.waiting_count,
            oldestWaitingSinceAt: result.oldest_waiting_since_at,
          }))
          setAttentionFailure('waiting', false)
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) setAttentionFailure('waiting', true)
      })
    return () => controller.abort()
  }, [refreshKey, session, setAttentionFailure])

  return { attention, data, errors, hasLoaded, isRefreshing, products, retry }
}
