import type { LossReason, OpportunityStatus, OpportunitySummary } from '../pipeline/types'
import type { WonFilters } from '../won/types'

export type LostOpportunity = {
  opportunity: OpportunitySummary
  loss_event_id: number
  loss_reason: LossReason
  loss_reason_detail: string | null
  from_status: OpportunityStatus
  customer_province: string | null
  lost_at: string
  quoted_total_kg: string
  loss_products: Array<{ product_id: number; product_name: string; quantity_kg: string }>
}

export type LostOpportunityPage = { items: LostOpportunity[]; next_cursor: string | null }

export type LostStatistics = {
  current_count: number
  current_quantity_kg: string
  without_quote_count: number
  historical_loss_count: number
  historical_quantity_kg: string
  reopened_count: number
  current_by_reason: Array<{ key: LossReason; count: number; quantity_kg: string }>
  current_by_product: Array<{
    product_id: number
    product_name: string
    count: number
    quantity_kg: string
  }>
}

export type LostFilters = WonFilters & { reasons: LossReason[]; customerId: number | null }

export const EMPTY_LOST_FILTERS: LostFilters = {
  period: 'all',
  search: '',
  reasons: [],
  customerId: null,
  province: '',
  product: '',
  source: '',
  responsible: '',
  unassigned: false,
  from: '',
  to: '',
}
