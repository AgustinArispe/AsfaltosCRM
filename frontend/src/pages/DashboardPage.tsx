import { useMemo, useState } from 'react'

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
import { activeFilterCount, defaultDashboardFilters } from '../metrics/filters'
import { useDashboardMetrics } from '../metrics/useDashboardMetrics'
import { AppLink } from '../routing/router'
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
  hasWaitingConversation,
  staleTotal,
  unreadTotal,
  isUnavailable,
}: {
  hasWaitingConversation: boolean | null
  staleTotal: number | null
  unreadTotal: number | null
  isUnavailable: boolean
}) {
  const items = [
    {
      label: 'Seguimientos pendientes',
      value: staleTotal === null ? '—' : String(staleTotal),
      icon: 'clock' as IconName,
      target: 'notifications' as const,
      action: 'Ver seguimientos',
    },
    {
      label: 'Notificaciones sin leer',
      value: unreadTotal === null ? '—' : String(unreadTotal),
      icon: 'bell' as IconName,
      target: 'notifications' as const,
      action: 'Revisar notificaciones',
    },
    {
      label: 'Conversaciones esperando',
      value: hasWaitingConversation === null ? '—' : hasWaitingConversation ? 'Hay' : '0',
      icon: 'whatsapp' as IconName,
      target: 'whatsapp' as const,
      action: 'Abrir WhatsApp',
    },
  ]

  return (
    <section aria-labelledby='dashboard-attention-title' className='dashboard-attention'>
      <div className='dashboard-attention__heading'>
        <h2 id='dashboard-attention-title'>Lo que necesita seguimiento ahora</h2>
      </div>
      {isUnavailable ? (
        <p className='dashboard-attention__unavailable'>
          Parte de la evidencia operativa no está disponible en este momento.
        </p>
      ) : null}
      <ul>
        {items.map((item) => (
          <li className='dashboard-attention__item' key={item.label}>
            <span className='dashboard-attention__icon'>
              <Icon name={item.icon} />
            </span>
            <span className='dashboard-attention__content'>
              <strong className='dashboard-attention__value'>{item.value}</strong>
              <b>{item.label}</b>
            </span>
            <AppLink
              aria-label={`${item.action}: ${item.label.toLocaleLowerCase('es-AR')}`}
              className='dashboard-attention__action'
              to={{ kind: 'workspace', workspace: item.target }}
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
  const [filters, setFilters] = useState(() => defaultDashboardFilters())
  const session = useMemo<ApiSession>(
    () => ({ token: token ?? '', onUnauthorized: logout }),
    [logout, token],
  )
  const { attention, data, errors, hasLoaded, isRefreshing, products, retry } = useDashboardMetrics(
    filters,
    session,
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
            hasWaitingConversation={attention.hasWaitingConversation}
            isUnavailable={Boolean(errors.attention)}
            staleTotal={attention.staleTotal}
            unreadTotal={attention.unreadTotal}
          />
          {data.overview ? (
            <DashboardKpis overview={data.overview} />
          ) : (
            <EmptyState
              action={<DashboardRefresh isRefreshing={isRefreshing} onRetry={retry} />}
              description='No pudimos recuperar los indicadores clave.'
              title='Indicadores no disponibles'
            />
          )}
          <div className='dashboard-primary-grid'>
            <TimelineChart
              error={errors.timeline}
              filters={filters}
              hasActiveFilters={hasActiveFilters}
              onRetry={retry}
              session={session}
              timeline={data.timeline}
            />
            <ResultsCluster
              error={errors.pipeline}
              hasDimensionFilters={hasDimensionFilters}
              onRetry={retry}
              overview={data.overview}
              pipeline={data.pipeline}
            />
          </div>
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
