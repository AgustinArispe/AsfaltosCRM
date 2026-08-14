import type { LostFilters, LostOpportunityPage, LostStatistics } from '../lost/types'
import { apiRequest } from './client'
import type { ApiSession } from './opportunities'

function lostQuery(filters: LostFilters, cursor?: string | null, includeLimit = true): string {
  const query = new URLSearchParams()
  if (filters.search) query.set('search', filters.search)
  filters.reasons.forEach((reason) => {
    query.append('reason', reason)
  })
  if (filters.customerId) query.set('customer_id', String(filters.customerId))
  if (filters.province) query.set('province', filters.province)
  if (filters.productId) query.set('product_id', String(filters.productId))
  if (filters.source) query.set('source', filters.source)
  if (filters.lostFrom) query.set('lost_from', `${filters.lostFrom}T00:00:00Z`)
  if (filters.lostTo) query.set('lost_to', `${filters.lostTo}T00:00:00Z`)
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
