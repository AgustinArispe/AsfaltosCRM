import type {
  MetricsFilters,
  MetricsOverview,
  PipelineMetrics,
  ProductMetricsResponse,
  ProvinceMetricsResponse,
  SourceMetricsResponse,
  TimelineGranularity,
  TimelineMetrics,
} from '../metrics/types'
import { apiRequest } from './client'
import type { ApiSession } from './opportunities'

function dimensionQuery(filters: MetricsFilters): URLSearchParams {
  const query = new URLSearchParams()
  if (filters.source) query.set('source', filters.source)
  if (filters.productId) query.set('product_id', String(filters.productId))
  if (filters.province) query.set('province', filters.province)
  return query
}

function periodQuery(filters: MetricsFilters): URLSearchParams {
  const query = dimensionQuery(filters)
  query.set('from', filters.from)
  query.set('to', filters.to)
  return query
}

function endpoint(path: string, query: URLSearchParams): string {
  return `${path}?${query.toString()}`
}

export function getMetricsOverview(filters: MetricsFilters, session: ApiSession) {
  return apiRequest<MetricsOverview>(endpoint('/metrics/overview', periodQuery(filters)), session)
}

export function getProductMetrics(filters: MetricsFilters, session: ApiSession) {
  return apiRequest<ProductMetricsResponse>(
    endpoint('/metrics/products', periodQuery(filters)),
    session,
  )
}

export function getSourceMetrics(filters: MetricsFilters, session: ApiSession) {
  return apiRequest<SourceMetricsResponse>(
    endpoint('/metrics/sources', periodQuery(filters)),
    session,
  )
}

export function getProvinceMetrics(filters: MetricsFilters, session: ApiSession) {
  return apiRequest<ProvinceMetricsResponse>(
    endpoint('/metrics/provinces', periodQuery(filters)),
    session,
  )
}

export function getTimelineMetrics(
  filters: MetricsFilters,
  granularity: TimelineGranularity,
  session: ApiSession,
) {
  const query = periodQuery(filters)
  query.set('granularity', granularity)
  return apiRequest<TimelineMetrics>(endpoint('/metrics/timeline', query), session)
}

export function getPipelineMetrics(filters: MetricsFilters, session: ApiSession) {
  return apiRequest<PipelineMetrics>(
    endpoint('/metrics/pipeline', dimensionQuery(filters)),
    session,
  )
}
