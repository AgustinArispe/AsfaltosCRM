import { type CSSProperties, type ReactNode, useState } from 'react'

import type { ApiSession } from '../api/opportunities'
import { OPPORTUNITY_STATUS_LABELS } from '../pipeline/config'
import { AppLink } from '../routing/router'
import { Button } from '../shared/Button'
import { formatDateTime, formatDecimalKg, formatDecimalRatioPercent } from '../shared/formatters'
import { Icon } from '../shared/Icon'
import { SegmentedControl } from '../shared/SegmentedControl'
import { ChartSurface, EmptyState, ErrorState, Skeleton } from '../shared/StatusStates'
import { type DashboardFilters, dashboardOutcomeQuery, sourceLabel } from './filters'
import type {
  MetricsFilters,
  MetricsOverview,
  PipelineMetrics,
  ProductMetric,
  ProvinceMetric,
  SourceMetric,
  TimelineMetric,
  TimelineMetrics,
  TimelineSeries,
} from './types'
import { useTimelineDayDetail } from './useTimelineDayDetail'

type ChartError = string | undefined

function formatCount(value: number): string {
  return new Intl.NumberFormat('es-AR').format(value)
}

function SurfaceState({
  error,
  hasData,
  onRetry,
}: {
  error: ChartError
  hasData: boolean
  onRetry: () => void
}) {
  if (error && !hasData) return <ErrorState message={error} onRetry={onRetry} />
  if (error)
    return (
      <p className='dashboard-surface-error' role='status'>
        {error}
      </p>
    )
  return null
}

function ratio(value: string | null): string {
  return value === null ? '—' : formatDecimalRatioPercent(value)
}

export function DashboardKpis({
  overview,
  filters,
}: {
  overview: MetricsOverview
  filters: DashboardFilters
}) {
  const query = dashboardOutcomeQuery(filters)
  const opportunityDenominator = overview.opportunities.won + overview.opportunities.lost
  return (
    <section aria-labelledby='dashboard-result-title' className='dashboard-period-result'>
      <header className='dashboard-section-heading'>
        <div>
          <p className='dashboard-eyebrow'>Balance comercial</p>
          <h2 id='dashboard-result-title'>Resultado del período</h2>
        </div>
        <p>
          {filters.customStart} — {filters.customEnd}
        </p>
      </header>
      <div className='dashboard-outcomes'>
        <article className='dashboard-outcome dashboard-outcome--won'>
          <p>Ganadas</p>
          <strong>{formatCount(overview.opportunities.won)}</strong>
          <span>{formatDecimalKg(overview.volume_kg.won)} ganados</span>
          <AppLink to={`/won?${query}`}>Ver ganadas</AppLink>
        </article>
        <article className='dashboard-outcome dashboard-outcome--lost'>
          <p>Pérdidas</p>
          <strong>{formatCount(overview.opportunities.lost)}</strong>
          <span>{formatDecimalKg(overview.volume_kg.lost)} perdidos</span>
          <AppLink to={`/lost?${query}`}>Ver pérdidas</AppLink>
        </article>
        <dl className='dashboard-conversions'>
          <div>
            <dt>Conversión de oportunidades</dt>
            <dd>
              <strong>{ratio(overview.opportunities.conversion_rate)}</strong>
              <span>
                {opportunityDenominator === 0
                  ? 'Sin resultados cerrados en el período'
                  : `${formatCount(overview.opportunities.won)} ganadas de ${formatCount(opportunityDenominator)} resultados`}
              </span>
            </dd>
          </div>
          <div>
            <dt>Conversión de volumen</dt>
            <dd>
              <strong>{ratio(overview.volume_kg.conversion_rate)}</strong>
              <span>
                {overview.volume_kg.conversion_rate === null
                  ? 'Sin volumen cerrado en el período'
                  : 'Kg ganados / (kg ganados + kg perdidos)'}
              </span>
            </dd>
          </div>
        </dl>
      </div>
    </section>
  )
}

const ACTIVE_STATUSES = ['NUEVA', 'COTIZADA', 'NEGOCIACION'] as const

export function ResultsCluster({
  pipeline,
  error,
  onRetry,
  hasDimensionFilters,
}: {
  overview?: MetricsOverview
  pipeline?: PipelineMetrics
  error: ChartError
  onRetry: () => void
  hasDimensionFilters: boolean
}) {
  const items = ACTIVE_STATUSES.map(
    (status) => pipeline?.items.find((item) => item.status === status) ?? { status, count: 0 },
  )
  const total = items.reduce((sum, item) => sum + item.count, 0)
  return (
    <section aria-labelledby='active-opportunities-title' className='dashboard-active'>
      <div className='dashboard-section-heading'>
        <div>
          <p className='dashboard-eyebrow'>Foto actual</p>
          <h2 id='active-opportunities-title'>Oportunidades activas ahora</h2>
        </div>
        <AppLink to={{ kind: 'workspace', workspace: 'pipeline' }}>Ver Pipeline</AppLink>
      </div>
      <SurfaceState error={error} hasData={Boolean(pipeline)} onRetry={onRetry} />
      {!pipeline && !error ? <Skeleton className='dashboard-mini-skeleton' /> : null}
      {pipeline ? (
        <>
          <div className='dashboard-active__summary'>
            <strong>{formatCount(total)}</strong>
            <span>
              {hasDimensionFilters ? 'activas con los filtros actuales' : 'activas en total'}
            </span>
            <small>Snapshot {formatDateTime(pipeline.snapshot_at)}</small>
          </div>
          {total === 0 ? (
            <p className='dashboard-compact-empty'>No hay oportunidades activas ahora.</p>
          ) : (
            <>
              <div
                aria-label={items
                  .map((item) => `${OPPORTUNITY_STATUS_LABELS[item.status]}: ${item.count}`)
                  .join(', ')}
                className='dashboard-pipeline-bar'
                role='img'
              >
                {items.map((item) => (
                  <span
                    className={`dashboard-pipeline-bar__segment dashboard-pipeline-bar__segment--${item.status.toLowerCase()}`}
                    key={item.status}
                    style={{ flexGrow: item.count }}
                  />
                ))}
              </div>
              <ul className='dashboard-pipeline-list'>
                {items.map((item) => (
                  <li key={item.status}>
                    <span
                      className={`dashboard-marker dashboard-marker--${item.status.toLowerCase()}`}
                    />
                    <span>{OPPORTUNITY_STATUS_LABELS[item.status]}</span>
                    <b>{formatCount(item.count)}</b>
                    <em>{`${Math.round((item.count / total) * 100)} %`}</em>
                  </li>
                ))}
              </ul>
            </>
          )}
        </>
      ) : null}
    </section>
  )
}

function bucketLabel(bucket: string, granularity: TimelineMetrics['granularity']): string {
  const start = new Date(`${bucket}T12:00:00-03:00`)
  if (granularity === 'week') {
    const end = new Date(start)
    end.setUTCDate(end.getUTCDate() + 6)
    const short = (value: Date) =>
      new Intl.DateTimeFormat('es-AR', {
        day: 'numeric',
        month: 'short',
        timeZone: 'America/Argentina/Buenos_Aires',
      }).format(value)
    return `${short(start)}–${short(end)}`
  }
  return new Intl.DateTimeFormat('es-AR', {
    day: granularity === 'day' ? 'numeric' : undefined,
    month: 'short',
    year: 'numeric',
    timeZone: 'America/Argentina/Buenos_Aires',
  }).format(start)
}

const SERIES: Array<{
  key: TimelineSeries
  label: string
  value: (item: TimelineMetric) => number
}> = [
  { key: 'created', label: 'Creadas', value: (item) => item.leads_created },
  { key: 'won', label: 'Ganadas', value: (item) => item.won },
  { key: 'lost', label: 'Pérdidas', value: (item) => item.lost },
]

export function TimelineChart({
  timeline,
  error,
  onRetry,
  hasActiveFilters,
  filters,
  session,
}: {
  timeline?: TimelineMetrics
  error: ChartError
  onRetry: () => void
  hasActiveFilters: boolean
  filters: MetricsFilters
  session: ApiSession
}) {
  const detail = useTimelineDayDetail(filters, session)
  const maximum = Math.max(
    0,
    ...(timeline?.items.flatMap((item) => SERIES.map((series) => series.value(item))) ?? []),
  )
  return (
    <ChartSurface showTitle={false} title='Evolución comercial'>
      <div className='dashboard-timeline'>
        <div className='dashboard-chart-heading'>
          <div>
            <p className='dashboard-eyebrow'>Movimiento del período</p>
            <h2>Evolución comercial</h2>
            <p className='dashboard-chart-context'>
              Creadas, ganadas y pérdidas comparadas en el tiempo.
            </p>
          </div>
          <ul aria-label='Series de evolución' className='dashboard-series-legend'>
            {SERIES.map((series) => (
              <li className={`dashboard-series-${series.key}`} key={series.key}>
                <span />
                {series.label}
              </li>
            ))}
          </ul>
        </div>
        <SurfaceState error={error} hasData={Boolean(timeline)} onRetry={onRetry} />
        {!timeline && !error ? <Skeleton className='dashboard-chart-skeleton' /> : null}
        {timeline?.items.length ? (
          <div className='dashboard-comparison-chart'>
            <p className='dashboard-bar-chart__scale'>Máximo {formatCount(maximum)}</p>
            <ol style={{ '--dashboard-bar-count': timeline.items.length } as CSSProperties}>
              {timeline.items.map((bucket) => (
                <li key={bucket.bucket}>
                  <div className='dashboard-comparison-chart__bars'>
                    {SERIES.map((series) => {
                      const value = series.value(bucket)
                      const label = bucketLabel(bucket.bucket, timeline.granularity)
                      const style = {
                        '--dashboard-bar-height': `${maximum ? (value / maximum) * 100 : 0}%`,
                      } as CSSProperties
                      return timeline.granularity === 'day' && value > 0 ? (
                        <button
                          aria-label={`${label}: ${series.label} ${formatCount(value)}, abrir oportunidades`}
                          className={`dashboard-comparison-bar dashboard-series-${series.key}`}
                          key={series.key}
                          onClick={() => detail.open(bucket.bucket, series.key)}
                          style={style}
                          type='button'
                        />
                      ) : (
                        <span
                          aria-label={`${label}: ${series.label} ${formatCount(value)}`}
                          className={`dashboard-comparison-bar dashboard-series-${series.key}`}
                          key={series.key}
                          role='img'
                          style={style}
                        />
                      )
                    })}
                  </div>
                  <span>{bucketLabel(bucket.bucket, timeline.granularity)}</span>
                </li>
              ))}
            </ol>
          </div>
        ) : null}
        {timeline && timeline.items.length === 0 ? (
          <EmptyState
            description={
              hasActiveFilters
                ? 'Probá restablecer o ampliar los filtros.'
                : 'No hay actividad comercial en el período seleccionado.'
            }
            title='No hay evolución en el período'
          />
        ) : null}
        {detail.selected ? (
          <section aria-label='Oportunidades del día seleccionado' className='dashboard-day-detail'>
            <header>
              <h3>Detalle del día</h3>
              <Button
                aria-label='Cerrar detalle del día'
                onClick={detail.close}
                size='compact'
                variant='ghost'
              >
                <Icon name='close' />
              </Button>
            </header>
            {detail.isLoading && detail.items.length === 0 ? (
              <p role='status'>Cargando oportunidades…</p>
            ) : null}
            {detail.error ? <p className='dashboard-surface-error'>{detail.error}</p> : null}
            <ul>
              {detail.items.map((item) => (
                <li key={`${item.opportunity_id}-${item.loss_event_id ?? 'current'}`}>
                  <AppLink
                    to={{
                      kind: 'opportunity',
                      opportunityId: item.opportunity_id,
                      surface: item.current_status === 'PERDIDA' ? 'lost' : 'pipeline',
                    }}
                  >
                    {item.customer_name}
                  </AppLink>
                  <span>
                    {OPPORTUNITY_STATUS_LABELS[item.current_status]} · {sourceLabel(item.source)}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        ) : null}
        {timeline ? <TimelineTable timeline={timeline} /> : null}
      </div>
    </ChartSurface>
  )
}

function TimelineTable({ timeline }: { timeline: TimelineMetrics }) {
  return (
    <details className='dashboard-data-table'>
      <summary>Ver datos exactos de evolución</summary>
      <section aria-label='Tabla de evolución comercial'>
        <table>
          <thead>
            <tr>
              <th>Período</th>
              <th>Creadas</th>
              <th>Ganadas</th>
              <th>Pérdidas</th>
              <th>Kg ganados</th>
              <th>Kg perdidos</th>
            </tr>
          </thead>
          <tbody>
            {timeline.items.map((item) => (
              <tr key={item.bucket}>
                <th>{bucketLabel(item.bucket, timeline.granularity)}</th>
                <td>{formatCount(item.leads_created)}</td>
                <td>{formatCount(item.won)}</td>
                <td>{formatCount(item.lost)}</td>
                <td>{formatDecimalKg(item.kg_won)}</td>
                <td>{formatDecimalKg(item.kg_lost)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </details>
  )
}

type RankedItem = { label: string; value: number; displayValue: string; detail: string }

function RankedBars({ items, ariaLabel }: { items: RankedItem[]; ariaLabel: string }) {
  const maximum = Math.max(0, ...items.map((item) => item.value))
  return (
    <ol aria-label={ariaLabel} className='dashboard-ranked-bars'>
      {items.map((item) => (
        <li key={item.label}>
          <div>
            <span>{item.label}</span>
            <b>{item.displayValue}</b>
          </div>
          <div aria-hidden='true' className='dashboard-ranked-bars__track'>
            <span style={{ width: `${maximum ? (item.value / maximum) * 100 : 0}%` }} />
          </div>
          <small>{item.detail}</small>
        </li>
      ))}
    </ol>
  )
}

function DistributionState({
  items,
  error,
  onRetry,
  children,
}: {
  items: unknown[] | undefined
  error: ChartError
  onRetry: () => void
  children: ReactNode
}) {
  if (!items && !error) return <Skeleton className='dashboard-list-skeleton' />
  if (error && !items) return <ErrorState message={error} onRetry={onRetry} />
  if (items?.length === 0)
    return <p className='dashboard-compact-empty'>No hay datos para esta dimensión.</p>
  return (
    <>
      {children}
      {error ? <p className='dashboard-surface-error'>{error}</p> : null}
    </>
  )
}

export function CommercialDistribution({
  products,
  sources,
  provinces,
  errors,
  onRetry,
}: {
  products?: ProductMetric[]
  sources?: SourceMetric[]
  provinces?: ProvinceMetric[]
  errors: { products?: string; sources?: string; provinces?: string }
  onRetry: () => void
  hasActiveFilters: boolean
}) {
  const [secondary, setSecondary] = useState<'products' | 'provinces'>('products')
  const sourceTotal = sources?.reduce((sum, item) => sum + item.created, 0) ?? 0
  const sourceItems = sources
    ?.map((item) => ({
      label: sourceLabel(item.source),
      value: item.created,
      displayValue: formatCount(item.created),
      detail: sourceTotal
        ? `${Math.round((item.created / sourceTotal) * 100)} % de las creadas`
        : 'Sin oportunidades creadas',
    }))
    .sort((a, b) => b.value - a.value)
  const productItems = products
    ?.map((item) => ({
      label: item.product_name,
      value: Number(item.kg_quoted),
      displayValue: formatDecimalKg(item.kg_quoted),
      detail: `${formatCount(item.opportunities_quoted)} oportunidades cotizadas`,
    }))
    .sort((a, b) => b.value - a.value)
  const provinceItems = provinces
    ?.map((item) => ({
      label: item.province ?? 'Sin provincia',
      value: item.opportunities_created,
      displayValue: formatCount(item.opportunities_created),
      detail: `${formatDecimalKg(item.kg_quoted)} cotizados`,
    }))
    .sort((a, b) => b.value - a.value)
  const selectedItems = secondary === 'products' ? productItems : provinceItems
  const selectedError = secondary === 'products' ? errors.products : errors.provinces
  return (
    <div className='dashboard-distributions'>
      <section aria-labelledby='dashboard-origin-title' className='dashboard-origin'>
        <div className='dashboard-section-heading'>
          <div>
            <p className='dashboard-eyebrow'>Adquisición</p>
            <h2 id='dashboard-origin-title'>Origen de oportunidades</h2>
            <p>¿De dónde vienen nuestras oportunidades?</p>
          </div>
        </div>
        <DistributionState error={errors.sources} items={sources} onRetry={onRetry}>
          {sourceItems ? (
            <RankedBars
              ariaLabel={sourceItems
                .map((item) => `${item.label}: ${item.displayValue}, ${item.detail}`)
                .join(', ')}
              items={sourceItems}
            />
          ) : null}
        </DistributionState>
      </section>
      <section aria-labelledby='dashboard-secondary-title' className='dashboard-secondary'>
        <div className='dashboard-section-heading'>
          <div>
            <p className='dashboard-eyebrow'>Análisis secundario</p>
            <h2 id='dashboard-secondary-title'>Productos y provincias</h2>
          </div>
          <SegmentedControl
            label='Análisis secundario'
            onChange={(value) => setSecondary(value as 'products' | 'provinces')}
            segments={[
              { value: 'products', label: 'Productos' },
              { value: 'provinces', label: 'Provincias' },
            ]}
            value={secondary}
          />
        </div>
        <p className='dashboard-chart-context'>
          {secondary === 'products'
            ? 'Kg cotizados actuales de oportunidades creadas en el período.'
            : 'Oportunidades creadas en el período por provincia.'}
        </p>
        <DistributionState error={selectedError} items={selectedItems} onRetry={onRetry}>
          {selectedItems ? (
            <RankedBars
              ariaLabel={selectedItems
                .map((item) => `${item.label}: ${item.displayValue}`)
                .join(', ')}
              items={selectedItems}
            />
          ) : null}
        </DistributionState>
      </section>
    </div>
  )
}

export function DashboardRefresh({
  isRefreshing,
  onRetry,
}: {
  isRefreshing: boolean
  onRetry: () => void
}) {
  return (
    <Button aria-live='polite' onClick={onRetry} size='compact' variant='ghost'>
      <Icon
        className={isRefreshing ? 'size-4 animate-spin motion-reduce:animate-none' : 'size-4'}
        name='refresh'
      />
      {isRefreshing ? 'Actualizando…' : 'Actualizar'}
    </Button>
  )
}

export function meaningfulPeakIndexes(values: readonly number[]): number[] {
  const maximum = Math.max(0, ...values)
  if (maximum <= 0) return []
  const indexes = values.flatMap((value, index) => (value === maximum ? [index] : []))
  return indexes.length <= 2 ? indexes : []
}
