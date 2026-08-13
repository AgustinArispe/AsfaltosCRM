import type { CustomerSummary } from '../customers/types'
import type { Product as ProductModel } from '../products/types'

export type LeadSource = 'WEB' | 'WHATSAPP'

export type OpportunityStatus = 'NUEVA' | 'COTIZADA' | 'NEGOCIACION' | 'GANADA' | 'PERDIDA'

export type PipelineStatus = Exclude<OpportunityStatus, 'PERDIDA'>

export type LossReason = 'PRECIO' | 'SIN_RESPUESTA' | 'COMPETENCIA' | 'PROYECTO_CANCELADO' | 'OTRO'

export type Product = ProductModel

export type OpportunityCustomer = CustomerSummary

export type OpportunityUser = {
  id: number
  full_name: string
  email: string
}

export type QuotedProduct = {
  product: Product
  quantity_kg: string
}

export type OpportunitySummary = {
  id: number
  status: OpportunityStatus
  source: LeadSource
  current_status_entered_at: string
  customer: OpportunityCustomer
  assigned_user: OpportunityUser | null
  products: QuotedProduct[]
  created_at: string
  is_reopened?: boolean
  reopen_count?: number
}

export type OpportunityStatusHistory = {
  id: number
  from_status: OpportunityStatus | null
  to_status: OpportunityStatus
  changed_at: string
  changed_by_user_id: number | null
}

export type OpportunityDetail = OpportunitySummary & {
  history: OpportunityStatusHistory[]
  loss_reason: LossReason | null
  updated_at: string
}

export type PaginatedResponse<T> = {
  items: T[]
  page: number
  page_size: number
  total: number
}

export type QuoteProductInput = {
  product_id: number
  quantity_kg: number
}

export type OpportunityNote = {
  id: number
  opportunity_id: number
  author_user_id: number
  author_name: string
  created_at: string
  current_revision: {
    id: number
    revision_number: number
    body: string
    is_pinned: boolean
    actor_user_id: number
    actor_name: string
    created_at: string
  }
}

export type OpportunityNotePage = { items: OpportunityNote[]; next_cursor: string | null }
