export type LeadSource = 'WEB' | 'WHATSAPP'

export type OpportunityStatus =
  | 'NUEVA'
  | 'COTIZADA'
  | 'NEGOCIACION'
  | 'GANADA'
  | 'PERDIDA'

export type PipelineStatus = Exclude<OpportunityStatus, 'PERDIDA'>

export type LossReason =
  | 'PRECIO'
  | 'SIN_RESPUESTA'
  | 'COMPETENCIA'
  | 'PROYECTO_CANCELADO'
  | 'OTRO'

export type Product = {
  id: number
  name: string
  is_active: boolean
}

export type OpportunityCustomer = {
  id: number
  name: string
  company: string | null
  email: string | null
  phone: string | null
  province: string | null
  legendary_historical_override: boolean
}

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
