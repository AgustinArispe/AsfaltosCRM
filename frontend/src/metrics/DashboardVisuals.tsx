import { type CSSProperties, useState } from 'react'

import { Button } from '../shared/Button'
import { formatDateTime, formatDecimalKg, formatDecimalRatioPercent } from '../shared/formatters'
import { SegmentedControl } from '../shared/SegmentedControl'
import { ChartSurface, EmptyState, ErrorState, Skeleton } from '../shared/StatusStates'
import { sourceLabel } from './filters'
import type {
  MetricsOverview,
  PipelineMetrics,
  ProductMetric,
  ProvinceMetric,
  SourceMetric,
  TimelineMetric,
  TimelineMetrics,
} from './types'

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
  return value === null
    ? 'Sin oportunidades cerradas en el período'
    : formatDecimalRatioPercent(value)
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

type TimelineSeries = 'created' | 'won' | 'lost'

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

export function TimelineChart({
  timeline,
  error,
  onRetry,
  hasActiveFilters,
}: {
  timeline?: TimelineMetrics
  error: ChartError
  onRetry: () => void
  hasActiveFilters: boolean
}) {
  const [seriesKey, setSeriesKey] = useState<TimelineSeries>('created')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const series = TIMELINE_SERIES[seriesKey]
  const values = timeline?.items.map(series.value) ?? []
  const maximum = Math.max(0, ...values)
  const safeSelectedIndex = Math.min(selectedIndex, Math.max(0, values.length - 1))
  const selected = timeline?.items[safeSelectedIndex]
  const labelStride = Math.max(1, Math.ceil(values.length / 8))

  return (
    <ChartSurface showTitle={false} title='Evolución comercial'>
      <div className='dashboard-chart-heading'>
        <div>
          <h2>Evolución comercial</h2>
          <p className='dashboard-chart-context'>
            Creadas usa fecha de alta; ganadas y perdidas, fecha de cierre.
          </p>
        </div>
        <SegmentedControl
          label='Serie de evolución'
          onChange={(value) => {
            setSeriesKey(value as TimelineSeries)
            setSelectedIndex(0)
          }}
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
                return (
                  <li key={bucket.bucket}>
                    <button
                      aria-label={`${label}: ${series.label} ${formatCount(value)}`}
                      aria-pressed={safeSelectedIndex === index}
                      className={`dashboard-bar-chart__bar ${series.className}`}
                      onClick={() => setSelectedIndex(index)}
                      onFocus={() => setSelectedIndex(index)}
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
          <TimelineTable timeline={timeline} />
        </>
      ) : null}
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

type DonutItem = { label: string; value: number; detail?: string }

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
      <ul className='dashboard-donut__legend'>
        {items.map((item, index) => (
          <li key={item.label}>
            <span className={`dashboard-marker dashboard-marker--series-${index + 1}`} />
            <span>
              {item.label}
              {item.detail ? <small>{item.detail}</small> : null}
            </span>
            <b>{formatCount(item.value)}</b>
            <em>{total === 0 ? '—' : `${Math.round((item.value / total) * 100)} %`}</em>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function ConversionChart({ overview }: { overview?: MetricsOverview }) {
  const won = overview?.opportunities.won ?? 0
  const lost = overview?.opportunities.lost ?? 0
  const rate = overview?.opportunities.conversion_rate ?? null
  return (
    <ChartSurface showTitle={false} title='Resultados cerrados'>
      <h2>Resultados cerrados</h2>
      {overview ? (
        rate === null ? (
          <div className='dashboard-conversion-empty'>
            <strong>Sin oportunidades cerradas</strong>
            <span>No se calcula una tasa como 0 % sin denominador.</span>
          </div>
        ) : (
          <>
            <p className='dashboard-chart-context'>
              Conversión {formatDecimalRatioPercent(rate)} · Ganadas sobre total cerrado
            </p>
            <Donut
              ariaLabel={`Resultados cerrados: ${won} ganadas y ${lost} perdidas; conversión ${formatDecimalRatioPercent(rate)}`}
              items={[
                { label: 'Ganadas', value: won },
                { label: 'Perdidas', value: lost },
              ]}
              palette='outcome'
            />
          </>
        )
      ) : (
        <Skeleton className='dashboard-mini-skeleton' />
      )}
    </ChartSurface>
  )
}

const PIPELINE_LABELS = {
  NUEVA: 'Nueva',
  COTIZADA: 'Cotizada',
  NEGOCIACION: 'Negociación',
  GANADA: 'Ganada',
  PERDIDA: 'Perdida',
} as const

export function PipelineSnapshot({
  pipeline,
  error,
  onRetry,
  hasDimensionFilters,
}: {
  pipeline?: PipelineMetrics
  error: ChartError
  onRetry: () => void
  hasDimensionFilters: boolean
}) {
  const total = pipeline?.items.reduce((sum, item) => sum + item.count, 0) ?? 0
  return (
    <ChartSurface showTitle={false} title='Pipeline actual'>
      <h2>Distribución vigente</h2>
      <p className='dashboard-chart-context'>
        No se filtra por período. Snapshot{' '}
        {pipeline ? formatDateTime(pipeline.snapshot_at) : 'actual'}.
      </p>
      <SurfaceState error={error} hasData={Boolean(pipeline)} onRetry={onRetry} />
      {!pipeline && !error ? <Skeleton className='dashboard-mini-skeleton' /> : null}
      {pipeline && total === 0 ? (
        <EmptyState
          description={
            hasDimensionFilters
              ? 'Restablecé los filtros de dimensión para volver al snapshot completo.'
              : 'No hay oportunidades en el snapshot actual.'
          }
          title={
            hasDimensionFilters
              ? 'No hay Pipeline para estos filtros'
              : 'Pipeline sin oportunidades'
          }
        />
      ) : null}
      {pipeline && total > 0 ? (
        <>
          <div
            aria-label='Segmentos del Pipeline actual'
            className='dashboard-pipeline-bar'
            role='img'
          >
            {pipeline.items.map((item) => (
              <span
                className={`dashboard-pipeline-bar__segment dashboard-pipeline-bar__segment--${item.status.toLowerCase()}`}
                key={item.status}
                style={{ flexGrow: item.count }}
                title={`${PIPELINE_LABELS[item.status]}: ${item.count}`}
              >
                <span className='sr-only'>
                  {PIPELINE_LABELS[item.status]}: {formatCount(item.count)}
                </span>
              </span>
            ))}
          </div>
          <ul className='dashboard-pipeline-list'>
            {pipeline.items.map((item) => (
              <li key={item.status}>
                <span
                  className={`dashboard-marker dashboard-marker--${item.status.toLowerCase()}`}
                />
                {PIPELINE_LABELS[item.status]} <b>{formatCount(item.count)}</b>
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </ChartSurface>
  )
}

type RankedItem = { label: string; value: number; detail: string }

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
                <td>{formatCount(item.value)}</td>
                <td>{item.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </details>
  )
}

function RankedBars({
  title,
  items,
  empty,
  hasActiveFilters,
}: {
  title: string
  items: RankedItem[]
  empty: string
  hasActiveFilters: boolean
}) {
  const maximum = Math.max(1, ...items.map((item) => item.value))
  return items.length === 0 ? (
    <EmptyState
      description={
        hasActiveFilters
          ? 'Probá restablecer o ampliar los filtros.'
          : 'No hay actividad comercial en el período seleccionado.'
      }
      title={hasActiveFilters ? 'No hay resultados para estos filtros' : empty}
    />
  ) : (
    <>
      <ol aria-label={title} className='dashboard-ranked-bars'>
        {items.map((item) => (
          <li key={item.label}>
            <div>
              <span title={item.label}>{item.label}</span>
              <b>{formatCount(item.value)}</b>
            </div>
            <div className='dashboard-ranked-bars__track'>
              <span style={{ width: `${(item.value / maximum) * 100}%` }} />
            </div>
            <small>{item.detail}</small>
          </li>
        ))}
      </ol>
      <ExactDataTable items={items} title={title} />
    </>
  )
}

export function ProductRanking({
  items,
  error,
  onRetry,
  hasActiveFilters,
}: {
  items?: ProductMetric[]
  error: ChartError
  onRetry: () => void
  hasActiveFilters: boolean
}) {
  const ranked =
    items?.map((item) => ({
      label: item.product_name,
      value: Number(item.kg_quoted),
      detail: `${formatDecimalKg(item.kg_quoted)} · ${formatCount(item.opportunities_quoted)} cotizadas`,
    })) ?? []
  return (
    <ChartSurface showTitle={false} title='Productos'>
      <h2>Volumen cotizado por producto</h2>
      <SurfaceState error={error} hasData={Boolean(items)} onRetry={onRetry} />
      {!items && !error ? <Skeleton className='dashboard-list-skeleton' /> : null}
      {items ? (
        <RankedBars
          empty='No hay productos cotizados'
          hasActiveFilters={hasActiveFilters}
          items={ranked}
          title='Productos por kg cotizados'
        />
      ) : null}
    </ChartSurface>
  )
}

export function SourceRanking({
  items,
  error,
  onRetry,
  hasActiveFilters,
}: {
  items?: SourceMetric[]
  error: ChartError
  onRetry: () => void
  hasActiveFilters: boolean
}) {
  const ranked =
    items?.map((item) => ({
      label: sourceLabel(item.source),
      value: item.created,
      detail:
        item.conversion_rate === null
          ? 'Sin oportunidades cerradas'
          : `Conversión ${formatDecimalRatioPercent(item.conversion_rate)}`,
    })) ?? []
  const total = ranked.reduce((sum, item) => sum + item.value, 0)
  return (
    <ChartSurface showTitle={false} title='Origen'>
      <h2>Leads por origen</h2>
      <SurfaceState error={error} hasData={Boolean(items)} onRetry={onRetry} />
      {!items && !error ? <Skeleton className='dashboard-list-skeleton' /> : null}
      {items && total === 0 ? (
        <EmptyState
          description={
            hasActiveFilters
              ? 'Probá restablecer los filtros.'
              : 'No hay actividad comercial en el período.'
          }
          title='No hay actividad por origen'
        />
      ) : null}
      {items && total > 0 ? (
        <>
          <Donut
            ariaLabel={ranked.map((item) => `${item.label}: ${item.value}`).join(', ')}
            items={ranked}
          />
          <ExactDataTable items={ranked} title='Origen por oportunidades creadas' />
        </>
      ) : null}
    </ChartSurface>
  )
}

function visualProvinceItems(items: RankedItem[]): RankedItem[] {
  if (items.length <= 5) return items
  const unassigned = items.find((item) => item.label === 'Sin provincia')
  const named = items.filter((item) => item.label !== 'Sin provincia')
  const visible = unassigned ? [unassigned, ...named.slice(0, 3)] : named.slice(0, 4)
  const visibleLabels = new Set(visible.map((item) => item.label))
  const remainder = items.filter((item) => !visibleLabels.has(item.label))
  return [
    ...visible,
    {
      label: 'Otras',
      value: remainder.reduce((sum, item) => sum + item.value, 0),
      detail: `${remainder.length} provincias agrupadas sólo en el gráfico`,
    },
  ]
}

export function ProvinceRanking({
  items,
  error,
  onRetry,
  hasActiveFilters,
}: {
  items?: ProvinceMetric[]
  error: ChartError
  onRetry: () => void
  hasActiveFilters: boolean
}) {
  const ranked = [...(items ?? [])]
    .sort(
      (left, right) =>
        right.opportunities_created - left.opportunities_created ||
        (left.province ?? '').localeCompare(right.province ?? '', 'es-AR'),
    )
    .map((item) => ({
      label: item.province ?? 'Sin provincia',
      value: item.opportunities_created,
      detail: `${formatDecimalKg(item.kg_quoted)} cotizados · ${ratioLabel(item.conversion_rate)}`,
    }))
  const total = ranked.reduce((sum, item) => sum + item.value, 0)
  const visualItems = visualProvinceItems(ranked)
  return (
    <ChartSurface showTitle={false} title='Actividad por provincia'>
      <h2>Actividad por provincia</h2>
      <p className='dashboard-chart-context'>
        Top de actividad; Otras agrupa sólo la vista visual. La tabla conserva cada provincia.
      </p>
      <SurfaceState error={error} hasData={Boolean(items)} onRetry={onRetry} />
      {!items && !error ? <Skeleton className='dashboard-list-skeleton' /> : null}
      {items && total === 0 ? (
        <EmptyState
          description={
            hasActiveFilters
              ? 'Probá restablecer los filtros.'
              : 'No hay actividad comercial en el período.'
          }
          title='No hay actividad provincial'
        />
      ) : null}
      {items && total > 0 ? (
        <>
          <Donut
            ariaLabel={visualItems.map((item) => `${item.label}: ${item.value}`).join(', ')}
            items={visualItems}
          />
          <ExactDataTable items={ranked} title='Provincias por oportunidades creadas' />
        </>
      ) : null}
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
      {isRefreshing ? 'Actualizando…' : 'Actualizar'}
    </Button>
  )
}
