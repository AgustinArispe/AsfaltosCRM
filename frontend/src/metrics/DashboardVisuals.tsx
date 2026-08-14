import { useMemo, useState } from 'react'

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
        <p>Conversión de oportunidades</p>
        <strong>{ratioLabel(opportunities.conversion_rate)}</strong>
        <span>Ganadas / cerradas</span>
      </article>
      <article className='dashboard-kpi'>
        <p>Kg cotizados</p>
        <strong>{formatDecimalKg(volume.quoted)}</strong>
        <span>En oportunidades creadas</span>
      </article>
      <article className='dashboard-kpi'>
        <p>Volumen ganado</p>
        <strong>{formatDecimalKg(volume.won)}</strong>
        <span>Conversión por volumen: {ratioLabel(volume.conversion_rate)}</span>
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

type TrendMeasure = 'opportunities' | 'volume'

type TrendSeries = {
  label: string
  values: number[]
  className: string
  exact: (index: number) => string
}

function timelineSeries(timeline: TimelineMetrics, measure: TrendMeasure): TrendSeries[] {
  if (measure === 'volume') {
    return [
      {
        label: 'Kg ganados',
        values: timeline.items.map((item) => Number(item.kg_won)),
        className: 'dashboard-trend__line dashboard-trend__line--won',
        exact: (index) => formatDecimalKg(timeline.items[index].kg_won),
      },
      {
        label: 'Kg perdidos',
        values: timeline.items.map((item) => Number(item.kg_lost)),
        className: 'dashboard-trend__line dashboard-trend__line--lost',
        exact: (index) => formatDecimalKg(timeline.items[index].kg_lost),
      },
    ]
  }
  return [
    {
      label: 'Leads creados',
      values: timeline.items.map((item) => item.leads_created),
      className: 'dashboard-trend__line dashboard-trend__line--created',
      exact: (index) => formatCount(timeline.items[index].leads_created),
    },
    {
      label: 'Ganadas',
      values: timeline.items.map((item) => item.won),
      className: 'dashboard-trend__line dashboard-trend__line--won',
      exact: (index) => formatCount(timeline.items[index].won),
    },
    {
      label: 'Perdidas',
      values: timeline.items.map((item) => item.lost),
      className: 'dashboard-trend__line dashboard-trend__line--lost',
      exact: (index) => formatCount(timeline.items[index].lost),
    },
  ]
}

function pathForSeries(values: number[], maximum: number): string {
  const width = 640
  const height = 192
  const padding = 18
  return values
    .map((value, index) => {
      const x =
        values.length < 2
          ? width / 2
          : (index / (values.length - 1)) * (width - padding * 2) + padding
      const y = height - padding - (maximum === 0 ? 0 : (value / maximum) * (height - padding * 2))
      return `${index === 0 ? 'M' : 'L'}${x.toFixed(2)} ${y.toFixed(2)}`
    })
    .join(' ')
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
  const [measure, setMeasure] = useState<TrendMeasure>('opportunities')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const series = useMemo(
    () => (timeline ? timelineSeries(timeline, measure) : []),
    [measure, timeline],
  )
  const maximum = Math.max(0, ...series.flatMap((item) => item.values))
  const selected =
    timeline?.items[Math.min(selectedIndex, Math.max(0, (timeline?.items.length ?? 1) - 1))]
  const hasData = Boolean(timeline)

  return (
    <ChartSurface showTitle={false} title='Evolución comercial'>
      <div className='dashboard-chart-heading'>
        <div>
          <p className='dashboard-surface-kicker'>Evolución comercial</p>
          <h2>Actividad y resultados en el tiempo</h2>
        </div>
        <SegmentedControl
          label='Medida de evolución'
          onChange={(value) => {
            setMeasure(value as TrendMeasure)
            setSelectedIndex(0)
          }}
          segments={[
            { value: 'opportunities', label: 'Oportunidades' },
            { value: 'volume', label: 'Volumen' },
          ]}
          value={measure}
        />
      </div>
      <p className='dashboard-chart-context'>
        Leads creados por fecha de creación; resultados por ingreso al estado terminal.
      </p>
      <SurfaceState error={error} hasData={hasData} onRetry={onRetry} />
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
          <ul className='dashboard-legend' aria-label='Series de evolución'>
            {series.map((item) => (
              <li className={`dashboard-legend__item ${item.className}`} key={item.label}>
                {item.label}
              </li>
            ))}
          </ul>
          <fieldset className='dashboard-trend'>
            <legend className='sr-only'>Gráfico de evolución comercial</legend>
            <svg
              viewBox='0 0 640 192'
              role='img'
              aria-labelledby='timeline-chart-title timeline-chart-description'
            >
              <title id='timeline-chart-title'>Evolución comercial</title>
              <desc id='timeline-chart-description'>
                Usá el control de período para revisar valores exactos. La tabla ofrece el detalle
                completo.
              </desc>
              {[0.25, 0.5, 0.75].map((line) => (
                <line
                  className='dashboard-trend__grid'
                  key={line}
                  x1='18'
                  x2='622'
                  y1={18 + line * 156}
                  y2={18 + line * 156}
                />
              ))}
              <text className='dashboard-trend__axis-label' x='18' y='13'>
                Máx. visible {formatCount(Math.round(maximum))}
              </text>
              <text className='dashboard-trend__axis-label' x='18' y='190'>
                {bucketLabel(timeline.items[0].bucket, timeline.granularity)}
              </text>
              <text className='dashboard-trend__axis-label' textAnchor='end' x='622' y='190'>
                {bucketLabel(
                  timeline.items[timeline.items.length - 1].bucket,
                  timeline.granularity,
                )}
              </text>
              {series.map((item) => (
                <path
                  className={item.className}
                  d={pathForSeries(item.values, maximum)}
                  fill='none'
                  key={item.label}
                />
              ))}
              {timeline.items.map((bucket, index) => {
                const value = series[0]?.values[index] ?? 0
                const x =
                  timeline.items.length < 2 ? 320 : (index / (timeline.items.length - 1)) * 604 + 18
                const y = 174 - (maximum === 0 ? 0 : (value / maximum) * 156)
                return (
                  <foreignObject height='16' key={bucket.bucket} width='16' x={x - 8} y={y - 8}>
                    <button
                      aria-label={`${bucketLabel(bucket.bucket, timeline.granularity)}: ${series.map((item) => `${item.label} ${item.exact(index)}`).join(', ')}`}
                      className='dashboard-trend__point-button'
                      onMouseEnter={() => setSelectedIndex(index)}
                      tabIndex={-1}
                      type='button'
                    />
                  </foreignObject>
                )
              })}
            </svg>
            <label className='sr-only' htmlFor='dashboard-timeline-point'>
              Período de evolución
            </label>
            <input
              aria-valuetext={`${bucketLabel(selected?.bucket ?? timeline.items[0].bucket, timeline.granularity)}: ${series.map((item) => `${item.label} ${item.exact(Math.min(selectedIndex, timeline.items.length - 1))}`).join(', ')}`}
              className='dashboard-trend__range'
              id='dashboard-timeline-point'
              max={timeline.items.length - 1}
              min='0'
              onChange={(event) => setSelectedIndex(Number(event.target.value))}
              type='range'
              value={Math.min(selectedIndex, timeline.items.length - 1)}
            />
          </fieldset>
          {selected ? (
            <p className='dashboard-chart-tooltip' role='status'>
              <b>{bucketLabel(selected.bucket, timeline.granularity)}</b>
              {series.map((item) => (
                <span key={item.label}>
                  {item.label}: {item.exact(Math.min(selectedIndex, timeline.items.length - 1))}
                </span>
              ))}
            </p>
          ) : null}
          <TimelineTable measure={measure} timeline={timeline} />
        </>
      ) : null}
    </ChartSurface>
  )
}

function TimelineTable({
  timeline,
  measure,
}: {
  timeline: TimelineMetrics
  measure: TrendMeasure
}) {
  return (
    <details className='dashboard-data-table'>
      <summary>Ver datos exactos de evolución</summary>
      <section aria-label='Tabla de evolución comercial'>
        <table>
          <thead>
            <tr>
              <th>Período</th>
              {measure === 'opportunities' ? (
                <>
                  <th>Leads creados</th>
                  <th>Ganadas</th>
                  <th>Perdidas</th>
                </>
              ) : (
                <>
                  <th>Kg ganados</th>
                  <th>Kg perdidos</th>
                </>
              )}
            </tr>
          </thead>
          <tbody>
            {timeline.items.map((item) => (
              <tr key={item.bucket}>
                <th>{bucketLabel(item.bucket, timeline.granularity)}</th>
                {measure === 'opportunities' ? (
                  <>
                    <td>{formatCount(item.leads_created)}</td>
                    <td>{formatCount(item.won)}</td>
                    <td>{formatCount(item.lost)}</td>
                  </>
                ) : (
                  <>
                    <td>{formatDecimalKg(item.kg_won)}</td>
                    <td>{formatDecimalKg(item.kg_lost)}</td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </details>
  )
}

export function ConversionChart({ overview }: { overview?: MetricsOverview }) {
  const rate = overview?.opportunities.conversion_rate ?? null
  const won = overview?.opportunities.won ?? 0
  const lost = overview?.opportunities.lost ?? 0
  const ratio = rate === null ? null : Number(rate)
  const circumference = 2 * Math.PI * 42
  return (
    <ChartSurface showTitle={false} title='Conversión'>
      <p className='dashboard-surface-kicker'>Conversión</p>
      <h2>Resultados cerrados</h2>
      {overview ? (
        rate === null ? (
          <div className='dashboard-conversion-empty'>
            <strong>Sin oportunidades cerradas</strong>
            <span>No se calcula una tasa como 0 % sin denominador.</span>
          </div>
        ) : (
          <div className='dashboard-conversion'>
            <svg
              aria-label={`Conversión de oportunidades ${formatDecimalRatioPercent(rate)}; ${won} ganadas y ${lost} perdidas`}
              viewBox='0 0 120 120'
              role='img'
            >
              <circle className='dashboard-ring__track' cx='60' cy='60' r='42' />
              <circle
                className='dashboard-ring__value'
                cx='60'
                cy='60'
                r='42'
                strokeDasharray={`${circumference * (ratio ?? 0)} ${circumference}`}
              />
              <text className='dashboard-ring__text' x='60' y='64'>
                {formatDecimalRatioPercent(rate)}
              </text>
            </svg>
            <ul>
              <li>
                <span className='dashboard-marker dashboard-marker--won' />
                Ganadas <b>{formatCount(won)}</b>
              </li>
              <li>
                <span className='dashboard-marker dashboard-marker--lost' />
                Perdidas <b>{formatCount(lost)}</b>
              </li>
            </ul>
          </div>
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
      <p className='dashboard-surface-kicker'>Pipeline actual</p>
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
      <p className='dashboard-surface-kicker'>Productos</p>
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
  return (
    <ChartSurface showTitle={false} title='Origen'>
      <p className='dashboard-surface-kicker'>Origen</p>
      <h2>Leads creados por canal</h2>
      <SurfaceState error={error} hasData={Boolean(items)} onRetry={onRetry} />
      {!items && !error ? <Skeleton className='dashboard-list-skeleton' /> : null}
      {items ? (
        <RankedBars
          empty='No hay actividad por origen'
          hasActiveFilters={hasActiveFilters}
          items={ranked}
          title='Origen por oportunidades creadas'
        />
      ) : null}
    </ChartSurface>
  )
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
  return (
    <ChartSurface showTitle={false} title='Actividad por provincia'>
      <p className='dashboard-surface-kicker'>Actividad por provincia</p>
      <h2>¿De qué zonas viene la actividad?</h2>
      <p className='dashboard-chart-context'>
        Ranking por oportunidades creadas; Sin provincia conserva el historial disponible.
      </p>
      <SurfaceState error={error} hasData={Boolean(items)} onRetry={onRetry} />
      {!items && !error ? <Skeleton className='dashboard-list-skeleton' /> : null}
      {items ? (
        <RankedBars
          empty='No hay actividad provincial'
          hasActiveFilters={hasActiveFilters}
          items={ranked}
          title='Provincias por oportunidades creadas'
        />
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
