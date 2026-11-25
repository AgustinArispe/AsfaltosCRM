import type { WonFilterOptions, WonFilters, WonPageResponse, WonStatistics } from '../won/types'
import { apiRequest } from './client'
import { closedOpportunityParams } from './closed-opportunity-filters'
import type { ApiSession } from './opportunities'

export function listWonOpportunities(
  filters: WonFilters,
  cursor: string | null,
  session: ApiSession,
) {
  const query = closedOpportunityParams(filters, 'won')
  query.set('limit', '20')
  if (cursor) query.set('cursor', cursor)
  return apiRequest<WonPageResponse>(`/won-opportunities?${query}`, session)
}
export function getWonStatistics(filters: WonFilters, session: ApiSession) {
  return apiRequest<WonStatistics>(
    `/won-opportunities/statistics?${closedOpportunityParams(filters, 'won')}`,
    session,
  )
}
export function getWonFilterOptions(session: ApiSession) {
  return apiRequest<WonFilterOptions>('/won-opportunities/filter-options', session)
}
