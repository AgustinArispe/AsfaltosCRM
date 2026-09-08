import { useEffect, useMemo, useState } from 'react'

import type { ApiSession } from '../api/opportunities'
import { useAuth } from '../auth/AuthContext'
import { DashboardFilters } from '../metrics/DashboardFilters'
import {
  CommercialDistribution,
  DashboardKpis,
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
import { useDashboardMetrics } from '../metrics/useDashboardMetrics'
import { useNotificationAttentionContext } from '../notifications/NotificationAttention'
import { AppLink } from '../routing/router'
import { formatStageDuration } from '../shared/formatters'
import { Icon, type IconName } from '../shared/Icon'
import { EmptyState, Skeleton } from '../shared/StatusStates'

function DashboardSkeleton() {
  return (
    <div aria-label='Cargando Dashboard' className='dashboard-skeleton' role='status'>
      <div className='dashboard-skeleton__attention'>
        <Skeleton className='h-14 w-full' />
        <Skeleton className='h-14 w-full' />
        <Skeleton className='h-14 w-full' />
      </div>
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

function OperationalAttention({
  staleTotal,
  waitingTotal,
  oldestWaitingSinceAt,
  isUnavailable,
}: {
  staleTotal: number | null
  waitingTotal: number | null
  oldestWaitingSinceAt: string | null
  isUnavailable: boolean
}) {
  const items = [
    {
      label: 'oportunidades sin seguimiento',
      value: staleTotal === null ? '—' : String(staleTotal),
      icon: 'clock' as IconName,
      target: '/notifications?view=active',
      action: 'Ver seguimientos',
      detail: '14 días o más sin cambio de etapa',
      visible: staleTotal === null || staleTotal > 0,
    },
    {
      label: 'conversaciones pendientes de respuesta',
      value: waitingTotal === null ? '—' : String(waitingTotal),
      icon: 'whatsapp' as IconName,
      target: '/whatsapp?waiting=true',
      action: 'Abrir pendientes',
      detail: oldestWaitingSinceAt
        ? `La más antigua espera ${formatStageDuration(oldestWaitingSinceAt).toLocaleLowerCase('es-AR')}`
        : 'Mensajes humanos aún sin respuesta válida',
      visible: waitingTotal === null || waitingTotal > 0,
    },
  ]
  const visibleItems = items.filter((item) => item.visible)
  const isCalm = staleTotal === 0 && waitingTotal === 0

  return (
    <section aria-labelledby='dashboard-attention-title' className='dashboard-attention'>
      <div className='dashboard-attention__heading'>
        <h2 id='dashboard-attention-title'>Necesita atención</h2>
      </div>
      {isUnavailable ? (
        <p className='dashboard-attention__unavailable'>
          Parte de la evidencia operativa no está disponible en este momento.
        </p>
      ) : null}
      {isCalm ? <p className='dashboard-attention__calm'>Sin pendientes urgentes</p> : null}
      <ul>
        {visibleItems.map((item) => (
          <li className='dashboard-attention__item' key={item.label}>
            <span className='dashboard-attention__icon'>
              <Icon name={item.icon} />
            </span>
            <span className='dashboard-attention__content'>
              <strong className='dashboard-attention__value'>{item.value}</strong>
              <b>{item.label}</b>
              <small>{item.detail}</small>
            </span>
            <AppLink
              aria-label={`${item.action}: ${item.label.toLocaleLowerCase('es-AR')}`}
              className='dashboard-attention__action'
              to={item.target}
            >
              {item.action}
              <Icon name='chevron-right' />
            </AppLink>
          </li>
        ))}
      </ul>
    </section>
  )
}

export function DashboardPage() {
  const { token, logout } = useAuth()
  const [filters, setFilters] = useState(() => dashboardFiltersFromQuery(window.location.search))
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
  const { attention, data, errors, hasLoaded, isRefreshing, products, retry } = useDashboardMetrics(
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
          <OperationalAttention
            isUnavailable={Boolean(errors.attention)}
            oldestWaitingSinceAt={attention.oldestWaitingSinceAt}
            staleTotal={attention.staleTotal}
            waitingTotal={attention.waitingTotal}
          />
          {data.overview ? (
            <DashboardKpis filters={filters} overview={data.overview} />
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
          />
          <TimelineChart
            error={errors.timeline}
            filters={filters}
            hasActiveFilters={hasActiveFilters}
            onRetry={retry}
            session={session}
            timeline={data.timeline}
          />
          <CommercialDistribution
            errors={{
              products: errors.products,
              provinces: errors.provinces,
              sources: errors.sources,
            }}
            hasActiveFilters={hasActiveFilters}
            onRetry={retry}
            products={data.products}
            provinces={data.provinces}
            sources={data.sources}
          />
        </>
      )}
    </section>
  )
}
