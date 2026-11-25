import type { WonFilters } from '../won/types'

export function closedOpportunityParams(
  filters: WonFilters,
  status: 'won' | 'lost',
): URLSearchParams {
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
  if (filters.from) query.set(`${status}_from`, `${filters.from}T00:00:00-03:00`)
  if (filters.to) {
    const next = new Date(`${filters.to}T00:00:00Z`)
    next.setUTCDate(next.getUTCDate() + 1)
    query.set(`${status}_to`, `${next.toISOString().slice(0, 10)}T00:00:00-03:00`)
  }
  return query
}
