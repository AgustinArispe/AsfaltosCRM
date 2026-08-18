import type { LeadSource, OpportunityStatus } from '../pipeline/types'

export type MetricPeriod = {
  from: string
  to: string
}

export type MetricsFilters = {
  from: string
  to: string
  source: LeadSource | null
  productId: number | null
  province: string | null
}

export type MetricsOverview = {
  period: MetricPeriod
  opportunities: {
    created: number
    won: number
    lost: number
    open: number
    conversion_rate: string | null
  }
  volume_kg: {
    quoted: string
    won: string
    lost: string
    open: string
    conversion_rate: string | null
  }
}

export type ProductMetric = {
  product_id: number
  product_name: string
  opportunities_quoted: number
  kg_quoted: string
  opportunities_won: number
  kg_won: string
  opportunities_lost: number
  kg_lost: string
  conversion_rate_opportunities: string | null
  conversion_rate_kg: string | null
}

export type SourceMetric = {
  source: LeadSource
  created: number
  won: number
  lost: number
  conversion_rate: string | null
}

export type ProvinceMetric = {
  province: string | null
  opportunities_created: number
  opportunities_won: number
  opportunities_lost: number
  conversion_rate: string | null
  kg_quoted: string
  kg_won: string
  kg_lost: string
}

export type TimelineGranularity = 'day' | 'month'
export type TimelineSeries = 'created' | 'won' | 'lost'

export type TimelineMetric = {
  bucket: string
  leads_created: number
  won: number
  lost: number
  kg_won: string
  kg_lost: string
}

export type TimelineMetrics = {
  period: MetricPeriod
  granularity: TimelineGranularity
  timezone: string
  items: TimelineMetric[]
}

export type TimelineDayOpportunityProduct = {
  product_id: number
  product_name: string
  quantity_kg: string
  is_active: boolean
}

export type TimelineDayOpportunity = {
  opportunity_id: number
  customer_name: string
  customer_company: string | null
  current_status: OpportunityStatus
  source: LeadSource
  products: TimelineDayOpportunityProduct[]
}

export type TimelineDayOpportunities = {
  bucket: string
  series: TimelineSeries
  timezone: string
  page: number
  page_size: number
  total: number
  items: TimelineDayOpportunity[]
}

export type PipelineStatusMetric = {
  status: OpportunityStatus
  count: number
}

export type PipelineMetrics = {
  snapshot_at: string
  items: PipelineStatusMetric[]
}

export type ProductMetricsResponse = { period: MetricPeriod; items: ProductMetric[] }
export type SourceMetricsResponse = { period: MetricPeriod; items: SourceMetric[] }
export type ProvinceMetricsResponse = { period: MetricPeriod; items: ProvinceMetric[] }

export type DashboardData = {
  overview: MetricsOverview
  products: ProductMetric[]
  sources: SourceMetric[]
  provinces: ProvinceMetric[]
  timeline: TimelineMetrics
  pipeline: PipelineMetrics
}
