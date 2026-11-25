import type { LostFilters, LostOpportunityPage, LostStatistics } from '../lost/types'
import type { WonFilterOptions } from '../won/types'
import { apiRequest } from './client'
import { closedOpportunityParams } from './closed-opportunity-filters'
import type { ApiSession } from './opportunities'

function lostQuery(filters: LostFilters, cursor?: string | null, includeLimit = true): string {
  const query = closedOpportunityParams(filters, 'lost')
  for (const reason of filters.reasons) query.append('reason', reason)
  if (filters.customerId) query.set('customer_id', String(filters.customerId))
  if (includeLimit) query.set('limit', '20')
  if (cursor) query.set('cursor', cursor)
  return query.toString()
}

export function listLostOpportunities(
  filters: LostFilters,
  cursor: string | null,
  session: ApiSession,
) {
  return apiRequest<LostOpportunityPage>(
    `/lost-opportunities?${lostQuery(filters, cursor)}`,
    session,
  )
}

export function getLostStatistics(filters: LostFilters, session: ApiSession) {
  return apiRequest<LostStatistics>(
    `/lost-opportunities/statistics?${lostQuery(filters, null, false)}`,
    session,
  )
}

export function getLostFilterOptions(session: ApiSession) {
  return apiRequest<WonFilterOptions>('/lost-opportunities/filter-options', session)
}
