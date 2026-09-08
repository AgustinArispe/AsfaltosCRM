import type { LeadSource, OpportunitySummary } from '../pipeline/types'

export type WonOpportunity = {
  opportunity: OpportunitySummary
  won_at: string
  won_total_kg: string
}
export type WonPageResponse = { items: WonOpportunity[]; next_cursor: string | null }
export type WonStatistics = { won_count: number; won_quantity_kg: string }
export type WonFilterOptions = {
  products: Array<{ id: number; name: string; is_active: boolean }>
  provinces: string[]
  responsible_users: Array<{ id: number; full_name: string; is_active: boolean }>
}
export type WonFilters = {
  period: 'month' | 'three-months' | 'year' | 'custom' | 'all'
  from: string
  to: string
  search: string
  product: string
  source: LeadSource | ''
  province: string
  responsible: string
  unassigned: boolean
}
