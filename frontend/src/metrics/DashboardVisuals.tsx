import { type CSSProperties, useEffect, useState } from 'react'

import type { ApiSession } from '../api/opportunities'
import { OPPORTUNITY_STATUS_LABELS } from '../pipeline/config'
import { AppLink } from '../routing/router'
import { Button } from '../shared/Button'
import { formatDateTime, formatDecimalKg, formatDecimalRatioPercent } from '../shared/formatters'
import { Icon } from '../shared/Icon'
import { SegmentedControl } from '../shared/SegmentedControl'
import { ChartSurface, EmptyState, ErrorState, Skeleton } from '../shared/StatusStates'
import { sourceLabel } from './filters'
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

function formatCount(value: number): string {
  return new Intl.NumberFormat('es-AR').format(value)
}

function ratioLabel(value: string | null): string {
  return value === null ? 'Sin oportunidades cerradas' : formatDecimalRatioPercent(value)
}

export function DashboardKpis({ overview }: { overview: MetricsOverview }) {
  const { opportunities, volume_kg: volume } = overview
  return (
    <section aria-label='Indicadores clave' className='dashboard-kpis'>
      <article className='dashboard-kpi dashboard-kpi--accent'>
        <p>Oportunidades creadas</p>
        <strong>{formatCount(opportunities.created)}</strong>
        <span>Creadas en el período</span>
      </article>
      <article className='dashboard-kpi'>
        <p>Resultados cerrados</p>
        <strong>{formatCount(opportunities.won + opportunities.lost)}</strong>
        <span>
          <b className='dashboard-text-success'>Ganadas {formatCount(opportunities.won)}</b> ·{' '}
          <b className='dashboard-text-loss'>Perdidas {formatCount(opportunities.lost)}</b>
        </span>
      </article>
      <article className='dashboard-kpi'>
        <p>Conversión</p>
        <strong>
          {opportunities.conversion_rate === null
            ? '—'
            : formatDecimalRatioPercent(opportunities.conversion_rate)}
        </strong>
        <span>
          {opportunities.conversion_rate === null
            ? 'Sin oportunidades cerradas'
            : 'Ganadas / cerradas'}
        </span>
      </article>
      <article className='dashboard-kpi'>
        <p>Kg cotizados</p>
        <strong>{formatDecimalKg(volume.quoted)}</strong>
        <span>En oportunidades creadas</span>
      </article>
      <article className='dashboard-kpi'>
        <p>Volumen ganado</p>
        <strong>{formatDecimalKg(volume.won)}</strong>
        <span>Conversión: {ratioLabel(volume.conversion_rate)}</span>
      </article>
    </section>
  )
}

function bucketLabel(bucket: string, granularity: TimelineMetrics['granularity']): string {
  return new Intl.DateTimeFormat('es-AR', {
    day: granularity === 'day' ? 'numeric' : undefined,
    month: 'short',
    year: 'numeric',
    timeZone: 'America/Argentina/Buenos_Aires',
  }).format(new Date(`${bucket}T12:00:00-03:00`))
}

const TIMELINE_SERIES: Record<
  TimelineSeries,
  { label: string; value: (item: TimelineMetric) => number; className: string }
> = {
  created: {
    label: 'Creadas',
    value: (item) => item.leads_created,
    className: 'dashboard-bar-chart__bar--created',
  },
  won: {
    label: 'Ganadas',
    value: (item) => item.won,
    className: 'dashboard-bar-chart__bar--won',
  },
  lost: {
    label: 'Perdidas',
    value: (item) => item.lost,
    className: 'dashboard-bar-chart__bar--lost',
  },
}

export function meaningfulPeakIndexes(values: readonly number[]): number[] {
  const maximum = Math.max(0, ...values)
  if (maximum <= 0) return []
  const indexes = values.flatMap((value, index) => (value === maximum ? [index] : []))
  return indexes.length <= 2 ? indexes : []
}

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
  const [seriesKey, setSeriesKey] = useState<TimelineSeries>('created')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const detail = useTimelineDayDetail(filters, session)
  const series = TIMELINE_SERIES[seriesKey]
  const values = timeline?.items.map(series.value) ?? []
  const maximum = Math.max(0, ...values)
  const peaks = new Set(meaningfulPeakIndexes(values))
  const safeSelectedIndex = Math.min(selectedIndex, Math.max(0, values.length - 1))
  const selected = timeline?.items[safeSelectedIndex]
  const labelStride = Math.max(1, Math.ceil(values.length / 7))

  useEffect(() => {
    if (!detail.selected) return
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') detail.close()
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [detail.close, detail.selected])

  const selectSeries = (value: string) => {
    detail.close()
    setSeriesKey(value as TimelineSeries)
    setSelectedIndex(0)
  }

  return (
    <ChartSurface showTitle={false} title='Evolución comercial'>
      <div className='dashboard-timeline'>
        <div className='dashboard-chart-heading'>
          <div>
            <h2>Evolución comercial</h2>
            <p className='dashboard-chart-context'>
              Creadas usa fecha de alta; ganadas y perdidas, fecha de cierre.
            </p>
          </div>
          <SegmentedControl
            label='Serie de evolución'
            onChange={selectSeries}
            segments={[
              { value: 'created', label: 'Creadas' },
              { value: 'won', label: 'Ganadas' },
              { value: 'lost', label: 'Perdidas' },
            ]}
            value={seriesKey}
          />
        </div>
        <SurfaceState error={error} hasData={Boolean(timeline)} onRetry={onRetry} />
        {!timeline && !error ? <Skeleton className='dashboard-chart-skeleton' /> : null}
        {timeline && timeline.items.length === 0 ? (
          <EmptyState
            description={
              hasActiveFilters
                ? 'Probá restablecer o ampliar los filtros.'
                : 'No hay actividad comercial en el período seleccionado.'
            }
            title={
              hasActiveFilters
                ? 'No hay resultados para estos filtros'
                : 'No hay evolución en el período'
            }
          />
        ) : null}
        {timeline && timeline.items.length > 0 ? (
          <>
            <fieldset className='dashboard-bar-chart'>
              <legend className='sr-only'>{series.label} por período</legend>
              <p className='dashboard-bar-chart__scale'>Máximo {formatCount(maximum)}</p>
              <ol
                className='dashboard-bar-chart__plot'
                style={{ '--dashboard-bar-count': timeline.items.length } as CSSProperties}
              >
                {timeline.items.map((bucket, index) => {
                  const value = values[index] ?? 0
                  const label = bucketLabel(bucket.bucket, timeline.granularity)
                  const showLabel =
                    index === 0 || index === timeline.items.length - 1 || index % labelStride === 0
                  const canOpen = timeline.granularity === 'day' && value > 0
                  return (
                    <li key={bucket.bucket}>
                      <button
                        aria-controls={canOpen ? 'timeline-day-detail' : undefined}
                        aria-expanded={
                          canOpen
                            ? detail.selected?.bucket === bucket.bucket &&
                              detail.selected.series === seriesKey
                            : undefined
                        }
                        aria-haspopup={canOpen ? 'dialog' : undefined}
                        aria-label={`${label}: ${series.label} ${formatCount(value)}${peaks.has(index) ? ', pico del período' : ''}${canOpen ? ', abrir oportunidades' : ''}`}
                        aria-pressed={safeSelectedIndex === index}
                        className={`${series.className} dashboard-bar-chart__bar${peaks.has(index) ? ' dashboard-bar-chart__bar--peak' : ''}`}
                        onClick={() => {
                          setSelectedIndex(index)
                          if (canOpen) detail.open(bucket.bucket, seriesKey)
                        }}
                        onFocus={() => {
                          setSelectedIndex(index)
                          if (canOpen) detail.open(bucket.bucket, seriesKey)
                        }}
                        onMouseEnter={() => setSelectedIndex(index)}
                        style={
                          {
                            '--dashboard-bar-height': `${maximum === 0 ? 0 : (value / maximum) * 100}%`,
                          } as CSSProperties
                        }
                        title={`${label}: ${formatCount(value)}`}
                        type='button'
                      >
                        <span className='sr-only'>{formatCount(value)}</span>
                      </button>
                      <span aria-hidden={!showLabel} className='dashboard-bar-chart__label'>
                        {showLabel ? label : ''}
                      </span>
                    </li>
                  )
                })}
              </ol>
            </fieldset>
            {selected ? (
              <p className='dashboard-chart-tooltip' role='status'>
                <b>{bucketLabel(selected.bucket, timeline.granularity)}</b>
                <span>
                  {series.label}: {formatCount(series.value(selected))}
                </span>
              </p>
            ) : null}
            {detail.selected ? (
              <section
                aria-label={`Oportunidades ${series.label.toLocaleLowerCase('es-AR')} del ${bucketLabel(detail.selected.bucket, 'day')}`}
                aria-modal='false'
                className='dashboard-day-detail'
                id='timeline-day-detail'
                role='dialog'
              >
                <header>
                  <div>
                    <span>{series.label}</span>
                    <h3>{bucketLabel(detail.selected.bucket, 'day')}</h3>
                  </div>
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
                  <p aria-live='polite'>Cargando oportunidades…</p>
                ) : null}
                {detail.error ? <p className='dashboard-surface-error'>{detail.error}</p> : null}
                {detail.items.length > 0 ? (
                  <ul>
                    {detail.items.map((item) => (
                      <li key={item.opportunity_id}>
                        <div>
                          <AppLink
                            origin={{ kind: 'workspace', workspace: 'dashboard' }}
                            to={{
                              kind: 'opportunity',
                              opportunityId: item.opportunity_id,
                              surface: item.current_status === 'PERDIDA' ? 'lost' : 'pipeline',
                            }}
                          >
                            {item.customer_name}
                          </AppLink>
                          {item.customer_company ? <span>{item.customer_company}</span> : null}
                        </div>
                        <p>
                          <b>{OPPORTUNITY_STATUS_LABELS[item.current_status]}</b> ·{' '}
                          {sourceLabel(item.source)}
                        </p>
                        {item.products.length > 0 ? (
                          <small>
                            {item.products
                              .map(
                                (product) =>
                                  `${product.product_name}: ${formatDecimalKg(product.quantity_kg)}`,
                              )
                              .join(' · ')}
                          </small>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                ) : null}
                {!detail.isLoading && !detail.error && detail.items.length === 0 ? (
                  <p>No hay oportunidades para este día.</p>
                ) : null}
                {detail.items.length < detail.total ? (
                  <Button
                    disabled={detail.isLoading}
                    onClick={detail.loadMore}
                    size='compact'
                    variant='secondary'
                  >
                    {detail.isLoading
                      ? 'Cargando…'
                      : `Ver más (${detail.items.length} de ${detail.total})`}
                  </Button>
                ) : null}
              </section>
            ) : null}
            <TimelineTable timeline={timeline} />
          </>
        ) : null}
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
              <th>Leads creados</th>
              <th>Ganadas</th>
              <th>Perdidas</th>
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

type RankedItem = { label: string; value: number; detail: string; displayValue?: string }
type DonutItem = Pick<RankedItem, 'label' | 'value' | 'detail' | 'displayValue'>

function Donut({
  items,
  ariaLabel,
  palette = 'categorical',
}: {
  items: DonutItem[]
  ariaLabel: string
  palette?: 'categorical' | 'outcome'
}) {
  const total = items.reduce((sum, item) => sum + item.value, 0)
  const circumference = 2 * Math.PI * 42
  let cumulative = 0
  return (
    <div className={`dashboard-donut dashboard-donut--${palette}`}>
      <svg aria-label={ariaLabel} role='img' viewBox='0 0 120 120'>
        <circle className='dashboard-donut__track' cx='60' cy='60' r='42' />
        {items.map((item, index) => {
          const ratio = total === 0 ? 0 : item.value / total
          const offset = -circumference * cumulative
          cumulative += ratio
          return (
            <circle
              className={`dashboard-donut__segment dashboard-donut__segment--${index + 1}`}
              cx='60'
              cy='60'
              key={item.label}
              r='42'
              strokeDasharray={`${circumference * ratio} ${circumference * (1 - ratio)}`}
              strokeDashoffset={offset}
            />
          )
        })}
        <text className='dashboard-donut__total' x='60' y='59'>
          {formatCount(total)}
        </text>
        <text className='dashboard-donut__caption' x='60' y='72'>
          total
        </text>
      </svg>
      <ol className='dashboard-donut__legend'>
        {items.map((item, index) => (
          <li key={item.label}>
            <span className={`dashboard-marker dashboard-marker--series-${index + 1}`} />
            <span>
              {item.label}
              <small>{item.detail}</small>
            </span>
            <b>{item.displayValue ?? formatCount(item.value)}</b>
            <em>{total === 0 ? '—' : `${Math.round((item.value / total) * 100)} %`}</em>
          </li>
        ))}
      </ol>
    </div>
  )
}

const PIPELINE_LABELS = {
  NUEVA: 'Nueva',
  COTIZADA: 'Cotizada',
  NEGOCIACION: 'Negociación',
  GANADA: 'Ganada',
  PERDIDA: 'Perdida',
} as const

const ACTIVE_PIPELINE_STATUSES = ['NUEVA', 'COTIZADA', 'NEGOCIACION', 'GANADA'] as const

export function ResultsCluster({
  overview,
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
  const won = overview?.opportunities.won ?? 0
  const lost = overview?.opportunities.lost ?? 0
  const rate = overview?.opportunities.conversion_rate ?? null
  const activeItems = ACTIVE_PIPELINE_STATUSES.map(
    (status) => pipeline?.items.find((item) => item.status === status) ?? { status, count: 0 },
  )
  const pipelineTotal = activeItems.reduce((sum, item) => sum + item.count, 0)
  return (
    <ChartSurface showTitle={false} title='Resultados y composición'>
      <div className='dashboard-results-cluster'>
        <section aria-labelledby='closed-results-title'>
          <h2 id='closed-results-title'>Resultados cerrados</h2>
          {overview ? (
            rate === null ? (
              <div className='dashboard-conversion-empty'>
                <strong>Sin oportunidades cerradas</strong>
                <span>No se calcula una tasa sin resultados cerrados.</span>
              </div>
            ) : (
              <>
                <p className='dashboard-chart-context'>
                  Conversión {formatDecimalRatioPercent(rate)} · Ganadas sobre total cerrado
                </p>
                <Donut
                  ariaLabel={`Resultados cerrados: ${won} ganadas y ${lost} perdidas; conversión ${formatDecimalRatioPercent(rate)}`}
                  items={[
                    { label: 'Ganadas', value: won, detail: 'Resultados ganados' },
                    { label: 'Perdidas', value: lost, detail: 'Resultados perdidos' },
                  ]}
                  palette='outcome'
                />
              </>
            )
          ) : (
            <Skeleton className='dashboard-mini-skeleton' />
          )}
        </section>
        <section aria-labelledby='pipeline-distribution-title'>
          <h2 id='pipeline-distribution-title'>Distribución vigente</h2>
          <p className='dashboard-chart-context'>
            Composición del Pipeline activo ·{' '}
            {pipeline ? formatDateTime(pipeline.snapshot_at) : 'Ahora'}
          </p>
          <SurfaceState error={error} hasData={Boolean(pipeline)} onRetry={onRetry} />
          {!pipeline && !error ? <Skeleton className='dashboard-mini-skeleton' /> : null}
          {pipeline && pipelineTotal === 0 ? (
            <EmptyState
              description={
                hasDimensionFilters
                  ? 'Restablecé los filtros de dimensión para ampliar el snapshot.'
                  : 'No hay oportunidades activas en este momento.'
              }
              size='small'
              title='Pipeline activo vacío'
            />
          ) : null}
          {pipeline && pipelineTotal > 0 ? (
            <>
              <div
                aria-label={activeItems
                  .map((item) => `${PIPELINE_LABELS[item.status]}: ${item.count}`)
                  .join(', ')}
                className='dashboard-pipeline-bar'
                role='img'
              >
                {activeItems.map((item) => (
                  <span
                    className={`dashboard-pipeline-bar__segment dashboard-pipeline-bar__segment--${item.status.toLowerCase()}`}
                    key={item.status}
                    style={{ flexGrow: item.count }}
                  />
                ))}
              </div>
              <ul className='dashboard-pipeline-list'>
                {activeItems.map((item) => (
                  <li key={item.status}>
                    <span
                      className={`dashboard-marker dashboard-marker--${item.status.toLowerCase()}`}
                    />
                    <span>{PIPELINE_LABELS[item.status]}</span>
                    <b>{formatCount(item.count)}</b>
                    <em>
                      {pipelineTotal === 0
                        ? '—'
                        : `${Math.round((item.count / pipelineTotal) * 100)} %`}
                    </em>
                  </li>
                ))}
              </ul>
            </>
          ) : null}
        </section>
      </div>
    </ChartSurface>
  )
}

function ExactDataTable({ title, items }: { title: string; items: RankedItem[] }) {
  return (
    <details className='dashboard-data-table'>
      <summary>Ver datos exactos de {title.toLocaleLowerCase('es-AR')}</summary>
      <section aria-label={`Tabla de ${title}`}>
        <table>
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Valor</th>
              <th>Contexto</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.label}>
                <th>{item.label}</th>
                <td>{item.displayValue ?? formatCount(item.value)}</td>
                <td>{item.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </details>
  )
}

export function topNWithOther(items: RankedItem[], limit = 4): RankedItem[] {
  if (items.length <= limit + 1) return items
  const visible = items.slice(0, limit)
  const remainder = items.slice(limit)
  const remainderValue = remainder.reduce((sum, item) => sum + item.value, 0)
  return [
    ...visible,
    {
      label: 'Otras',
      value: remainderValue,
      detail: `${remainder.length} categorías agrupadas sólo en el gráfico`,
      displayValue: remainder[0]?.displayValue?.includes('kg')
        ? formatDecimalKg(String(remainderValue))
        : undefined,
    },
  ]
}

type Dimension = 'products' | 'sources' | 'provinces'

export function CommercialDistribution({
  products,
  sources,
  provinces,
  errors,
  onRetry,
  hasActiveFilters,
}: {
  products?: ProductMetric[]
  sources?: SourceMetric[]
  provinces?: ProvinceMetric[]
  errors: { products?: string; sources?: string; provinces?: string }
  onRetry: () => void
  hasActiveFilters: boolean
}) {
  const [dimension, setDimension] = useState<Dimension>('products')
  const productItems: RankedItem[] = (products ?? [])
    .map((item) => ({
      label: item.product_name,
      value: Number(item.kg_quoted),
      displayValue: formatDecimalKg(item.kg_quoted),
      detail: `${formatCount(item.opportunities_quoted)} oportunidades cotizadas`,
    }))
    .sort(
      (left, right) => right.value - left.value || left.label.localeCompare(right.label, 'es-AR'),
    )
  const sourceItems: RankedItem[] = (sources ?? [])
    .map((item) => ({
      label: sourceLabel(item.source),
      value: item.created,
      detail:
        item.conversion_rate === null
          ? 'Sin oportunidades cerradas'
          : `Conversión ${formatDecimalRatioPercent(item.conversion_rate)}`,
    }))
    .sort(
      (left, right) => right.value - left.value || left.label.localeCompare(right.label, 'es-AR'),
    )
  const provinceItems: RankedItem[] = (provinces ?? [])
    .map((item) => ({
      label: item.province ?? 'Sin provincia',
      value: item.opportunities_created,
      detail: `${formatDecimalKg(item.kg_quoted)} cotizados · ${ratioLabel(item.conversion_rate)}`,
    }))
    .sort(
      (left, right) => right.value - left.value || left.label.localeCompare(right.label, 'es-AR'),
    )
  const definition = {
    products: {
      title: 'Productos por volumen cotizado',
      context: 'Kilogramos cotizados en oportunidades creadas durante el período.',
      items: productItems,
      source: products,
      error: errors.products,
    },
    sources: {
      title: 'Origen por oportunidades creadas',
      context: 'Origen de las oportunidades creadas durante el período.',
      items: sourceItems,
      source: sources,
      error: errors.sources,
    },
    provinces: {
      title: 'Provincias por oportunidades creadas',
      context: 'Actividad provincial; Otras agrupa únicamente la visualización.',
      items: provinceItems,
      source: provinces,
      error: errors.provinces,
    },
  }[dimension]
  const visualItems = topNWithOther(definition.items)
  const total = definition.items.reduce((sum, item) => sum + item.value, 0)
  return (
    <ChartSurface showTitle={false} title='Distribución comercial'>
      <div className='dashboard-dimension'>
        <div className='dashboard-chart-heading'>
          <div>
            <h2>Distribución comercial</h2>
            <p className='dashboard-chart-context'>{definition.context}</p>
          </div>
          <SegmentedControl
            label='Dimensión de distribución comercial'
            onChange={(value) => setDimension(value as Dimension)}
            segments={[
              { value: 'products', label: 'Productos' },
              { value: 'sources', label: 'Origen' },
              { value: 'provinces', label: 'Provincias' },
            ]}
            value={dimension}
          />
        </div>
        <SurfaceState
          error={definition.error}
          hasData={Boolean(definition.source)}
          onRetry={onRetry}
        />
        {!definition.source && !definition.error ? (
          <Skeleton className='dashboard-list-skeleton' />
        ) : null}
        {definition.source && total === 0 ? (
          <EmptyState
            description={
              hasActiveFilters
                ? 'Probá restablecer o ampliar los filtros.'
                : 'No hay actividad comercial en el período seleccionado.'
            }
            title='No hay datos para esta dimensión'
          />
        ) : null}
        {definition.source && total > 0 ? (
          <>
            <h3 className='sr-only'>{definition.title}</h3>
            <Donut
              ariaLabel={visualItems
                .map((item) => `${item.label}: ${item.displayValue ?? item.value}`)
                .join(', ')}
              items={visualItems}
            />
            <ExactDataTable items={definition.items} title={definition.title} />
          </>
        ) : null}
      </div>
    </ChartSurface>
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
