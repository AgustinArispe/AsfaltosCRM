import { useEffect, useMemo, useState } from 'react'

import type { ApiSession } from '../api/opportunities'
import { useAuth } from '../auth/AuthContext'
import { DashboardFilters } from '../metrics/DashboardFilters'
import {
  CommercialDistribution,
  DashboardKpis,
  DashboardLosses,
  DashboardRefresh,
  ResultsCluster,
  TimelineChart,
} from '../metrics/DashboardVisuals'
import {
  activeFilterCount,
  dashboardFiltersFromQuery,
  dashboardOutcomeQuery,
  defaultDashboardFilters,
} from '../metrics/filters'
import { type DrilldownSelection, MetricDrilldown } from '../metrics/MetricDrilldown'
import { useDashboardMetrics } from '../metrics/useDashboardMetrics'
import { useNotificationAttentionContext } from '../notifications/NotificationAttention'
import { EmptyState, Skeleton } from '../shared/StatusStates'

function DashboardSkeleton() {
  return (
    <div aria-label='Cargando Dashboard' className='dashboard-skeleton' role='status'>
      <div className='dashboard-skeleton__kpis'>
        {['created', 'closed', 'conversion', 'quoted', 'won'].map((label) => (
          <Skeleton className='h-28 w-full' key={label} />
        ))}
      </div>
      <Skeleton className='h-80 w-full' />
      <div className='dashboard-skeleton__paired'>
        <Skeleton className='h-56 w-full' />
        <Skeleton className='h-56 w-full' />
      </div>
    </div>
  )
}

export function DashboardPage() {
  const { token, logout } = useAuth()
  const [filters, setFilters] = useState(() => dashboardFiltersFromQuery(window.location.search))
  const [drilldown, setDrilldown] = useState<DrilldownSelection | null>(null)
  const session = useMemo<ApiSession>(
    () => ({ token: token ?? '', onUnauthorized: logout }),
    [logout, token],
  )
  useEffect(() => {
    window.history.replaceState(
      window.history.state,
      '',
      `/dashboard?${dashboardOutcomeQuery(filters)}`,
    )
  }, [filters])
  const notificationAttention = useNotificationAttentionContext()
  const { data, errors, hasLoaded, isRefreshing, products, retry } = useDashboardMetrics(
    filters,
    session,
    notificationAttention?.count ?? null,
  )
  const provinces = useMemo(
    () =>
      [
        ...new Set(
          (data.provinces ?? []).flatMap((item) => (item.province ? [item.province] : [])),
        ),
      ].sort((left, right) => left.localeCompare(right, 'es-AR')),
    [data.provinces],
  )
  const hasActiveFilters = activeFilterCount(filters) > 0
  const hasDimensionFilters = Boolean(filters.source || filters.productId || filters.province)

  return (
    <section aria-label='Dashboard comercial' className='dashboard-page'>
      <div aria-live='polite' className='sr-only'>
        {isRefreshing ? 'Actualizando Dashboard.' : ''}
      </div>
      <DashboardFilters
        action={<DashboardRefresh isRefreshing={isRefreshing} onRetry={retry} />}
        filters={filters}
        onChange={setFilters}
        onReset={() => setFilters(defaultDashboardFilters())}
        products={products}
        provinces={provinces}
      />
      {!hasLoaded ? (
        <DashboardSkeleton />
      ) : (
        <>
          {data.overview ? (
            <DashboardKpis filters={filters} onDrilldown={setDrilldown} overview={data.overview} />
          ) : (
            <EmptyState
              action={<DashboardRefresh isRefreshing={isRefreshing} onRetry={retry} />}
              description='No pudimos recuperar los indicadores clave.'
              title='Indicadores no disponibles'
            />
          )}
          <ResultsCluster
            error={errors.pipeline}
            hasDimensionFilters={hasDimensionFilters}
            onRetry={retry}
            overview={data.overview}
            pipeline={data.pipeline}
            onDrilldown={setDrilldown}
          />
          <TimelineChart
            error={errors.timeline}
            hasActiveFilters={hasActiveFilters}
            onDrilldown={setDrilldown}
            onRetry={retry}
            timeline={data.timeline}
          />
          <CommercialDistribution
            errors={{
              products: errors.products,
              provinces: errors.provinces,
              sources: errors.sources,
            }}
            hasActiveFilters={hasActiveFilters}
            lossesSection={<DashboardLosses onDrilldown={setDrilldown} products={data.products} />}
            onRetry={retry}
            products={data.products}
            provinces={data.provinces}
            sources={data.sources}
            onDrilldown={setDrilldown}
          />
          <MetricDrilldown
            filters={filters}
            onClose={() => setDrilldown(null)}
            selection={drilldown}
            session={session}
          />
        </>
      )}
    </section>
  )
}
