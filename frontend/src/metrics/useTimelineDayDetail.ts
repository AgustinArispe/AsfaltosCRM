import { useCallback, useEffect, useRef, useState } from 'react'

import { getTimelineDayOpportunities } from '../api/metrics'
import type { ApiSession } from '../api/opportunities'
import type { MetricsFilters, TimelineDayOpportunity, TimelineSeries } from './types'

type SelectedDay = { bucket: string; series: TimelineSeries }

export function useTimelineDayDetail(filters: MetricsFilters, session: ApiSession) {
  const [selected, setSelected] = useState<SelectedDay | null>(null)
  const [items, setItems] = useState<TimelineDayOpportunity[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const requestIdRef = useRef(0)
  const activeKeyRef = useRef<string | null>(null)
  const filtersKey = `${filters.from}|${filters.to}|${filters.source ?? ''}|${filters.productId ?? ''}|${filters.province ?? ''}`
  const previousFiltersKeyRef = useRef(filtersKey)

  useEffect(() => {
    if (previousFiltersKeyRef.current === filtersKey) return
    previousFiltersKeyRef.current = filtersKey
    requestIdRef.current += 1
    activeKeyRef.current = null
    setSelected(null)
    setItems([])
    setTotal(0)
    setPage(1)
    setError(null)
  }, [filtersKey])

  const load = useCallback(
    async (target: SelectedDay, targetPage: number, append: boolean) => {
      const requestId = requestIdRef.current + 1
      requestIdRef.current = requestId
      setIsLoading(true)
      setError(null)
      try {
        const response = await getTimelineDayOpportunities(
          filters,
          target.bucket,
          target.series,
          targetPage,
          session,
        )
        if (requestId !== requestIdRef.current) return
        setItems((current) => (append ? [...current, ...response.items] : response.items))
        setTotal(response.total)
        setPage(response.page)
      } catch (requestError) {
        if (requestId !== requestIdRef.current) return
        setError(
          requestError instanceof Error
            ? requestError.message
            : 'No pudimos cargar las oportunidades de este día.',
        )
      } finally {
        if (requestId === requestIdRef.current) setIsLoading(false)
      }
    },
    [filters, session],
  )

  const open = useCallback(
    (bucket: string, series: TimelineSeries) => {
      const key = `${bucket}:${series}`
      if (activeKeyRef.current === key) return
      activeKeyRef.current = key
      const target = { bucket, series }
      setSelected(target)
      setItems([])
      setTotal(0)
      setPage(1)
      void load(target, 1, false)
    },
    [load],
  )

  const close = useCallback(() => {
    requestIdRef.current += 1
    activeKeyRef.current = null
    setSelected(null)
    setItems([])
    setTotal(0)
    setError(null)
    setIsLoading(false)
  }, [])

  const loadMore = useCallback(() => {
    if (!selected || isLoading || items.length >= total) return
    void load(selected, page + 1, true)
  }, [isLoading, items.length, load, page, selected, total])

  return { close, error, isLoading, items, loadMore, open, selected, total }
}
