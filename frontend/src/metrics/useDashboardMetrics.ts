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
import { getActiveNotificationTotal, getNotificationTotal } from '../api/notifications'
import type { ApiSession } from '../api/opportunities'
import { listProducts } from '../api/products'
import { listWhatsAppConversations } from '../api/whatsapp'
import type { Product } from '../products/types'
import type { DashboardFilters } from './filters'
import { timelineGranularity } from './filters'
import type { DashboardData } from './types'

export type DashboardAttention = {
  staleTotal: number | null
  unreadTotal: number | null
  hasWaitingConversation: boolean | null
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

function fulfilled<T>(result: PromiseSettledResult<T>): T | null {
  return result.status === 'fulfilled' ? result.value : null
}

export function useDashboardMetrics(filters: DashboardFilters, session: ApiSession) {
  const [data, setData] = useState<Partial<DashboardData>>({})
  const [attention, setAttention] = useState<DashboardAttention>({
    staleTotal: null,
    unreadTotal: null,
    hasWaitingConversation: null,
  })
  const [products, setProducts] = useState<Product[]>([])
  const [errors, setErrors] = useState<DashboardErrors>({})
  const [hasLoaded, setHasLoaded] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const hasLoadedRef = useRef(false)
  const requestVersion = useRef(0)

  const retry = useCallback(() => setRefreshKey((value) => value + 1), [])

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
    const version = requestVersion.current + 1
    requestVersion.current = version
    setIsRefreshing(hasLoadedRef.current)

    const requestSession = { ...session, signal: controller.signal }
    const granularity = timelineGranularity(filters)
    void Promise.allSettled([
      getMetricsOverview(filters, requestSession),
      getProductMetrics(filters, requestSession),
      getSourceMetrics(filters, requestSession),
      getProvinceMetrics(filters, requestSession),
      getTimelineMetrics(filters, granularity, requestSession),
      getPipelineMetrics(filters, requestSession),
      getNotificationTotal(false, requestSession),
      getActiveNotificationTotal(requestSession),
      listWhatsAppConversations(
        { limit: 1, pageCursor: null, waitingOnly: true, unreadOnly: false, search: '' },
        requestSession,
      ),
    ]).then((results) => {
      if (controller.signal.aborted || requestVersion.current !== version) return
      const [
        overview,
        productsResult,
        sources,
        provinces,
        timeline,
        pipeline,
        stale,
        unread,
        waiting,
      ] = results
      const nextData: Partial<DashboardData> = {}
      const nextErrors: DashboardErrors = {}
      const overviewValue = fulfilled(overview)
      const productsValue = fulfilled(productsResult)
      const sourcesValue = fulfilled(sources)
      const provincesValue = fulfilled(provinces)
      const timelineValue = fulfilled(timeline)
      const pipelineValue = fulfilled(pipeline)

      if (overviewValue) nextData.overview = overviewValue
      else
        nextErrors.overview = dashboardErrorMessage(
          overview.status === 'rejected' ? overview.reason : null,
        )
      if (productsValue) nextData.products = productsValue.items
      else
        nextErrors.products = dashboardErrorMessage(
          productsResult.status === 'rejected' ? productsResult.reason : null,
        )
      if (sourcesValue) nextData.sources = sourcesValue.items
      else
        nextErrors.sources = dashboardErrorMessage(
          sources.status === 'rejected' ? sources.reason : null,
        )
      if (provincesValue) nextData.provinces = provincesValue.items
      else
        nextErrors.provinces = dashboardErrorMessage(
          provinces.status === 'rejected' ? provinces.reason : null,
        )
      if (timelineValue) nextData.timeline = timelineValue
      else
        nextErrors.timeline = dashboardErrorMessage(
          timeline.status === 'rejected' ? timeline.reason : null,
        )
      if (pipelineValue) nextData.pipeline = pipelineValue
      else
        nextErrors.pipeline = dashboardErrorMessage(
          pipeline.status === 'rejected' ? pipeline.reason : null,
        )

      const staleValue = fulfilled(stale)
      const unreadValue = fulfilled(unread)
      const waitingValue = fulfilled(waiting)
      if (!staleValue || !unreadValue || !waitingValue) nextErrors.attention = 'unavailable'
      setData((current) => ({ ...current, ...nextData }))
      setAttention({
        staleTotal: staleValue?.total ?? null,
        unreadTotal: unreadValue?.total ?? null,
        hasWaitingConversation: waitingValue ? waitingValue.items.length > 0 : null,
      })
      setErrors(nextErrors)
      hasLoadedRef.current = true
      setHasLoaded(true)
      setIsRefreshing(false)
    })
    return () => controller.abort()
  }, [filters, refreshKey, session])

  return { attention, data, errors, hasLoaded, isRefreshing, products, retry }
}
