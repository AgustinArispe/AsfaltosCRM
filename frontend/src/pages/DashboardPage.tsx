import { useMemo, useState } from 'react'

import type { ApiSession } from '../api/opportunities'
import { useAuth } from '../auth/AuthContext'
import { DashboardFilters } from '../metrics/DashboardFilters'
import {
  ConversionChart,
  DashboardKpis,
  DashboardRefresh,
  PipelineSnapshot,
  ProductRanking,
  ProvinceRanking,
  SourceRanking,
  TimelineChart,
} from '../metrics/DashboardVisuals'
import { activeFilterCount, defaultDashboardFilters } from '../metrics/filters'
import { useDashboardMetrics } from '../metrics/useDashboardMetrics'
import { AppLink } from '../routing/router'
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
  created,
  hasWaitingConversation,
  staleTotal,
  unreadTotal,
  isUnavailable,
}: {
  created: number | undefined
  hasWaitingConversation: boolean | null
  staleTotal: number | null
  unreadTotal: number | null
  isUnavailable: boolean
}) {
  const items = [
    staleTotal && staleTotal > 0
      ? {
          label: 'Seguimientos pendientes',
          value: String(staleTotal),
          description: 'Oportunidades sin cambio de estado durante 14 días o más.',
        }
      : null,
    unreadTotal && unreadTotal > 0
      ? {
          label: 'Notificaciones sin leer',
          value: String(unreadTotal),
          description: 'Total exacto de notificaciones activas pendientes de lectura.',
        }
      : null,
    hasWaitingConversation
      ? {
          label: 'Conversaciones esperando respuesta',
          value: 'Hay actividad',
          description: 'Existe al menos una conversación que requiere respuesta.',
        }
      : null,
  ].filter((item): item is NonNullable<typeof item> => item !== null)

  return (
    <section aria-labelledby='dashboard-attention-title' className='dashboard-attention'>
      <div className='dashboard-attention__heading'>
        <div>
          <p className='dashboard-surface-kicker'>Atención operativa</p>
          <h2 id='dashboard-attention-title'>Lo que necesita seguimiento ahora</h2>
        </div>
        {created !== undefined && created > 0 ? (
          <AppLink
            className='dashboard-attention__link'
            to={{ kind: 'workspace', workspace: 'pipeline' }}
          >
            Ver {created} creadas en Pipeline
          </AppLink>
        ) : null}
      </div>
      {items.length > 0 ? (
        <ul>
          {items.map((item) => (
            <li className='dashboard-attention__item' key={item.label}>
              <strong className='dashboard-attention__value'>{item.value}</strong>
              <span className='dashboard-attention__content'>
                <b>{item.label}</b>
                <small>{item.description}</small>
              </span>
            </li>
          ))}
        </ul>
      ) : isUnavailable ? (
        <p className='dashboard-attention__unavailable'>
          La evidencia operativa no está disponible en este momento.
        </p>
      ) : (
        <p className='dashboard-attention__calm'>
          Sin seguimientos o conversaciones esperando respuesta.
        </p>
      )}
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
    <section aria-labelledby='dashboard-workspace-title' className='dashboard-page'>
      <div aria-live='polite' className='sr-only'>
        {isRefreshing ? 'Actualizando Dashboard.' : ''}
      </div>
      <header className='dashboard-page-heading'>
        <div>
          <p className='dashboard-eyebrow'>Panorama comercial</p>
          <h2 id='dashboard-workspace-title'>Dashboard</h2>
          <p>Atención actual y desempeño comercial con métricas verificables.</p>
        </div>
        <DashboardRefresh isRefreshing={isRefreshing} onRetry={retry} />
      </header>
      <DashboardFilters
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
            created={data.overview?.opportunities.created}
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
              hasActiveFilters={hasActiveFilters}
              onRetry={retry}
              timeline={data.timeline}
            />
            <div className='dashboard-primary-grid__side'>
              <ConversionChart overview={data.overview} />
              <PipelineSnapshot
                error={errors.pipeline}
                hasDimensionFilters={hasDimensionFilters}
                onRetry={retry}
                pipeline={data.pipeline}
              />
            </div>
          </div>
          <div className='dashboard-secondary-grid'>
            <ProductRanking
              error={errors.products}
              hasActiveFilters={hasActiveFilters}
              items={data.products}
              onRetry={retry}
            />
            <SourceRanking
              error={errors.sources}
              hasActiveFilters={hasActiveFilters}
              items={data.sources}
              onRetry={retry}
            />
          </div>
          <ProvinceRanking
            error={errors.provinces}
            hasActiveFilters={hasActiveFilters}
            items={data.provinces}
            onRetry={retry}
          />
        </>
      )}
    </section>
  )
}
