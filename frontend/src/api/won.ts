import type { WonFilterOptions, WonFilters, WonPageResponse, WonStatistics } from '../won/types'
import { apiRequest } from './client'
import type { ApiSession } from './opportunities'

function params(filters: WonFilters): URLSearchParams {
  const query = new URLSearchParams()
  const values: Array<[string, string]> = [
    ['search', filters.search],
    ['product_id', filters.product],
    ['source', filters.source],
    ['province', filters.province],
    ['assigned_user_id', filters.responsible],
  ]
  values.forEach(([key, value]) => {
    if (value) query.set(key, value)
  })
  if (filters.unassigned) query.set('unassigned', 'true')
  if (filters.from) query.set('won_from', `${filters.from}T00:00:00-03:00`)
  if (filters.to) {
    const next = new Date(`${filters.to}T12:00:00-03:00`)
    next.setUTCDate(next.getUTCDate() + 1)
    query.set('won_to', next.toISOString())
  }
  return query
}

export function listWonOpportunities(
  filters: WonFilters,
  cursor: string | null,
  session: ApiSession,
) {
  const query = params(filters)
  query.set('limit', '20')
  if (cursor) query.set('cursor', cursor)
  return apiRequest<WonPageResponse>(`/won-opportunities?${query}`, session)
}
export function getWonStatistics(filters: WonFilters, session: ApiSession) {
  return apiRequest<WonStatistics>(`/won-opportunities/statistics?${params(filters)}`, session)
}
export function getWonFilterOptions(session: ApiSession) {
  return apiRequest<WonFilterOptions>('/won-opportunities/filter-options', session)
}
