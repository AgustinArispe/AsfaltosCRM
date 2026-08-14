import type { LeadSource, LossReason, OpportunitySummary } from '../pipeline/types'

export type LostOpportunity = {
  opportunity: OpportunitySummary
  loss_event_id: number
  loss_reason: LossReason
  lost_at: string
  quoted_total_kg: string
  loss_products: Array<{ product_id: number; product_name: string; quantity_kg: string }>
}

export type LostOpportunityPage = { items: LostOpportunity[]; next_cursor: string | null }

export type LostStatisticBucket = { key: string; count: number; quantity_kg: string }

export type LostStatistics = {
  current_count: number
  current_quantity_kg: string
  historical_loss_count: number
  historical_quantity_kg: string
  reopened_count: number
  by_reason: LostStatisticBucket[]
}

export type LostFilters = {
  search: string
  reasons: LossReason[]
  customerId: number | null
  province: string
  productId: number | null
  source: LeadSource | ''
  lostFrom: string
  lostTo: string
}

export const EMPTY_LOST_FILTERS: LostFilters = {
  search: '',
  reasons: [],
  customerId: null,
  province: '',
  productId: null,
  source: '',
  lostFrom: '',
  lostTo: '',
}
