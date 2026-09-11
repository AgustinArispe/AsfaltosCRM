import { type KeyboardEvent, type ReactNode, useState } from 'react'

import { OPPORTUNITY_STATUS_LABELS } from '../pipeline/config'
import { AppLink } from '../routing/router'
import { Button } from '../shared/Button'
import {
  formatCommercialPeriod,
  formatDecimalKg,
  formatDecimalRatioPercent,
} from '../shared/formatters'
import { Icon } from '../shared/Icon'
import { ChartSurface, ErrorState, Skeleton } from '../shared/StatusStates'
import { type DashboardFilters, sourceLabel } from './filters'
import type { DrilldownSelection } from './MetricDrilldown'
import type {
  MetricsOverview,
  PipelineMetrics,
  ProductMetric,
  ProvinceMetric,
  SourceMetric,
  TimelineMetric,
  TimelineMetrics,
  TimelineSeries,
} from './types'

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
  onDrilldown,
}: {
  overview: MetricsOverview
  filters: DashboardFilters
  onDrilldown: (selection: DrilldownSelection) => void
}) {
  const opportunityDenominator = overview.opportunities.won + overview.opportunities.lost
  return (
    <section aria-labelledby='dashboard-result-title' className='dashboard-period-result'>
      <header className='dashboard-section-heading'>
        <div>
          <h2 id='dashboard-result-title'>Resultado del período</h2>
        </div>
        <p className='dashboard-period-label'>
          {formatCommercialPeriod(filters.customStart, filters.customEnd)}
        </p>
      </header>
      <div className='dashboard-outcomes'>
        <button
          className='dashboard-outcome dashboard-outcome--won'
          onClick={() => onDrilldown({ title: 'Oportunidades ganadas', kind: 'won' })}
          type='button'
        >
          <span>
            <span className='dashboard-outcome__title'>
              <Icon name='trophy' />
              <b>Ganadas</b>
            </span>
            <Icon className='dashboard-card-chevron' name='chevron-right' />
          </span>
          <strong>{formatCount(overview.opportunities.won)} ganadas</strong>
          <em>{formatDecimalKg(overview.volume_kg.won)}</em>
        </button>
        <button
          className='dashboard-outcome dashboard-outcome--lost'
          onClick={() => onDrilldown({ title: 'Pérdidas del período', kind: 'lost' })}
          type='button'
        >
          <span>
            <span className='dashboard-outcome__title'>
              <Icon name='x-circle' />
              <b>Pérdidas</b>
            </span>
            <Icon className='dashboard-card-chevron' name='chevron-right' />
          </span>
          <strong>{formatCount(overview.opportunities.lost)} pérdidas</strong>
          <em>{formatDecimalKg(overview.volume_kg.lost)}</em>
        </button>
        <dl className='dashboard-conversions'>
          <div className='dashboard-conversion dashboard-conversion--opportunities'>
            <dt>
              <Icon name='target' />
              Conversión de oportunidades
            </dt>
            <dd>
              <strong>{ratio(overview.opportunities.conversion_rate)}</strong>
              <span>
                {opportunityDenominator === 0
                  ? 'Sin resultados cerrados en el período'
                  : `${formatCount(overview.opportunities.won)} ganadas de ${formatCount(opportunityDenominator)} resultados`}
              </span>
            </dd>
          </div>
          <div className='dashboard-conversion dashboard-conversion--volume'>
            <dt>
              <Icon name='chart-bars' />
              Conversión de volumen
            </dt>
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
const ACTIVE_DRILLDOWN_TITLES: Record<(typeof ACTIVE_STATUSES)[number], string> = {
  NUEVA: 'Oportunidades nuevas',
  COTIZADA: 'Oportunidades cotizadas',
  NEGOCIACION: 'Oportunidades en negociación',
}
const DONUT_CENTER = 56
const DONUT_RADIUS = 44

function donutPoint(fraction: number): { x: number; y: number } {
  const angle = fraction * Math.PI * 2 - Math.PI / 2
  return {
    x: DONUT_CENTER + DONUT_RADIUS * Math.cos(angle),
    y: DONUT_CENTER + DONUT_RADIUS * Math.sin(angle),
  }
}

function donutArcPath(startFraction: number, endFraction: number): string {
  const share = endFraction - startFraction
  if (share >= 1) {
    return `M ${DONUT_CENTER} ${DONUT_CENTER - DONUT_RADIUS} A ${DONUT_RADIUS} ${DONUT_RADIUS} 0 1 1 ${DONUT_CENTER} ${DONUT_CENTER + DONUT_RADIUS} A ${DONUT_RADIUS} ${DONUT_RADIUS} 0 1 1 ${DONUT_CENTER} ${DONUT_CENTER - DONUT_RADIUS}`
  }
  const start = donutPoint(startFraction)
  const end = donutPoint(endFraction)
  return `M ${start.x} ${start.y} A ${DONUT_RADIUS} ${DONUT_RADIUS} 0 ${share > 0.5 ? 1 : 0} 1 ${end.x} ${end.y}`
}

export function ResultsCluster({
  pipeline,
  error,
  onRetry,
  hasDimensionFilters,
  onDrilldown,
}: {
  overview?: MetricsOverview
  pipeline?: PipelineMetrics
  error: ChartError
  onRetry: () => void
  hasDimensionFilters: boolean
  onDrilldown: (selection: DrilldownSelection) => void
}) {
  const [highlightedStage, setHighlightedStage] = useState<(typeof ACTIVE_STATUSES)[number] | null>(
    null,
  )
  const items = ACTIVE_STATUSES.map((status) => ({
    status,
    count: pipeline?.items.find((item) => item.status === status)?.count ?? 0,
  }))
  const total = items.reduce((sum, item) => sum + item.count, 0)
  let usedFraction = 0
  const activateWithKeyboard = (
    event: KeyboardEvent<SVGPathElement>,
    selection: DrilldownSelection,
  ) => {
    if (event.key !== 'Enter' && event.key !== ' ') return
    event.preventDefault()
    onDrilldown(selection)
  }
  return (
    <section aria-labelledby='active-opportunities-title' className='dashboard-active'>
      <div className='dashboard-section-heading'>
        <div>
          <h2 id='active-opportunities-title'>Oportunidades activas</h2>
          <p>Distribución por etapa</p>
        </div>
        <AppLink to={{ kind: 'workspace', workspace: 'pipeline' }}>Ver oportunidades</AppLink>
      </div>
      <SurfaceState error={error} hasData={Boolean(pipeline)} onRetry={onRetry} />
      {!pipeline && !error ? <Skeleton className='dashboard-mini-skeleton' /> : null}
      {pipeline ? (
        <div className='dashboard-active__content'>
          <div className='dashboard-active-donut-wrap'>
            <svg
              aria-label='Distribución de oportunidades activas por etapa'
              className='dashboard-active-donut'
              viewBox='0 0 112 112'
            >
              <circle
                className='dashboard-active-donut__track'
                cx='56'
                cy='56'
                fill='none'
                r='44'
              />
              {items.map((item) => {
                const fraction = total ? item.count / total : 0
                if (item.count === 0) return null
                const startFraction = usedFraction
                usedFraction += fraction
                const selection: DrilldownSelection = {
                  title: ACTIVE_DRILLDOWN_TITLES[item.status],
                  kind: 'active',
                  status: item.status,
                }
                return (
                  // biome-ignore lint/a11y/useSemanticElements: SVG geometry cannot use a native HTML button; keyboard activation is implemented explicitly.
                  <path
                    aria-label={`${OPPORTUNITY_STATUS_LABELS[item.status]}: ${formatCount(item.count)}, ${Math.round(fraction * 100)} %; abrir detalle`}
                    className={`dashboard-active-donut__segment dashboard-active-donut__segment--${item.status.toLowerCase()} ${highlightedStage === item.status ? 'is-highlighted' : ''}`}
                    d={donutArcPath(startFraction, usedFraction)}
                    data-share={fraction}
                    fill='none'
                    key={item.status}
                    onBlur={() => setHighlightedStage(null)}
                    onClick={() => onDrilldown(selection)}
                    onFocus={() => setHighlightedStage(item.status)}
                    onKeyDown={(event) => activateWithKeyboard(event, selection)}
                    onMouseEnter={() => setHighlightedStage(item.status)}
                    onMouseLeave={() => setHighlightedStage(null)}
                    role='button'
                    tabIndex={0}
                  />
                )
              })}
            </svg>
            <button
              aria-label={`Ver las ${formatCount(total)} oportunidades activas`}
              className='dashboard-active-donut__center'
              onClick={() => onDrilldown({ title: 'Oportunidades activas', kind: 'active' })}
              type='button'
            >
              <strong>{formatCount(total)}</strong>
              <span>activas</span>
            </button>
          </div>
          <div>
            {hasDimensionFilters ? (
              <p className='dashboard-active__filter-note'>Con los filtros actuales</p>
            ) : null}
            <ul className='dashboard-stage-rows'>
              {items.map((item) => {
                const percentage = total ? Math.round((item.count / total) * 100) : 0
                return (
                  <li key={item.status}>
                    <button
                      aria-label={`Ver oportunidades en etapa ${OPPORTUNITY_STATUS_LABELS[item.status]}`}
                      className={`dashboard-stage-row dashboard-stage-row--${item.status.toLowerCase()} ${highlightedStage === item.status ? 'is-highlighted' : ''}`}
                      onBlur={() => setHighlightedStage(null)}
                      onClick={() =>
                        onDrilldown({
                          title: ACTIVE_DRILLDOWN_TITLES[item.status],
                          kind: 'active',
                          status: item.status,
                        })
                      }
                      onFocus={() => setHighlightedStage(item.status)}
                      onMouseEnter={() => setHighlightedStage(item.status)}
                      onMouseLeave={() => setHighlightedStage(null)}
                      type='button'
                    >
                      <span className='dashboard-stage-row__identity'>
                        <span className='dashboard-stage-row__dot' />
                        <span>{OPPORTUNITY_STATUS_LABELS[item.status]}</span>
                      </span>
                      <span className='dashboard-stage-row__metrics'>
                        <b>{formatCount(item.count)}</b>
                        <small>{percentage} %</small>
                      </span>
                      <Icon name='chevron-right' />
                    </button>
                  </li>
                )
              })}
            </ul>
          </div>
        </div>
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
    month: granularity === 'day' ? 'long' : 'short',
    year: granularity === 'day' ? undefined : 'numeric',
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

function chartTicks(maximum: number): number[] {
  return [...new Set([0, Math.ceil(maximum / 3), Math.ceil((maximum * 2) / 3), maximum])]
}

function dayNumber(bucket: string): number {
  return Number(bucket.slice(8, 10))
}

export function TimelineChart({
  timeline,
  error,
  onRetry,
  hasActiveFilters,
  onDrilldown,
}: {
  timeline?: TimelineMetrics
  error: ChartError
  onRetry: () => void
  hasActiveFilters: boolean
  onDrilldown: (selection: DrilldownSelection) => void
}) {
  const [hoveredBucket, setHoveredBucket] = useState<number | null>(null)
  const maximum = Math.max(
    0,
    ...(timeline?.items.flatMap((item) => SERIES.map((series) => series.value(item))) ?? []),
  )
  const scaleMaximum = Math.max(1, maximum)
  const chartWidth = 1000
  const chartHeight = 320
  const plotLeft = 48
  const plotRight = 982
  const plotTop = 24
  const plotBottom = 264
  const chartItems = timeline?.items ?? []
  const hasActivity = maximum > 0
  const slotWidth = chartItems.length ? (plotRight - plotLeft) / chartItems.length : 0
  const groupWidth = Math.min(21, slotWidth * 0.76)
  const barGap = Math.min(1.5, groupWidth * 0.08)
  const barWidth = Math.max(2, (groupWidth - barGap * 2) / SERIES.length)
  const bucketCenter = (index: number): number => plotLeft + slotWidth * (index + 0.5)
  const barHeight = (value: number): number => (value / scaleMaximum) * (plotBottom - plotTop)
  return (
    <ChartSurface showTitle={false} title='Evolución comercial'>
      <div className='dashboard-timeline'>
        <div className='dashboard-chart-heading'>
          <div>
            <h2>Evolución comercial</h2>
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
        {timeline?.items.length && hasActivity ? (
          <div className='dashboard-daily-chart'>
            <svg
              aria-label='Evolución comercial diaria'
              viewBox={`0 0 ${chartWidth} ${chartHeight}`}
            >
              {chartTicks(scaleMaximum).map((tick) => {
                const y = plotBottom - (tick / scaleMaximum) * (plotBottom - plotTop)
                return (
                  <g className='dashboard-daily-chart__grid' key={tick}>
                    <line x1={plotLeft} x2={plotRight} y1={y} y2={y} />
                    <text x='37' y={y + 4}>
                      {formatCount(tick)}
                    </text>
                  </g>
                )
              })}
              {hoveredBucket !== null ? (
                <rect
                  className='dashboard-daily-chart__hover-column'
                  height={plotBottom - plotTop + 30}
                  width={slotWidth}
                  x={plotLeft + hoveredBucket * slotWidth}
                  y={plotTop}
                />
              ) : null}
              {timeline.items.map((item, index) => {
                const groupLeft = bucketCenter(index) - groupWidth / 2
                return SERIES.map((series, seriesIndex) => {
                  const value = series.value(item)
                  if (value === 0) return null
                  const height = barHeight(value)
                  return (
                    <rect
                      className={`dashboard-daily-chart__bar dashboard-series-${series.key} ${hoveredBucket === index ? 'is-highlighted' : ''}`}
                      data-bucket={item.bucket}
                      data-series={series.key}
                      height={height}
                      key={`${item.bucket}-${series.key}`}
                      rx={Math.min(3, barWidth / 2)}
                      width={barWidth}
                      x={groupLeft + seriesIndex * (barWidth + barGap)}
                      y={plotBottom - height}
                    />
                  )
                })
              })}
              {timeline.items.map((item, index) => {
                const label = bucketLabel(item.bucket, timeline.granularity)
                return (
                  // biome-ignore lint/a11y/useSemanticElements: An SVG hit target is required to make each chart bucket independently keyboard accessible.
                  <rect
                    aria-label={`Abrir movimientos de ${label}: ${item.leads_created} creadas, ${item.won} ganadas, ${item.lost} pérdidas`}
                    className='dashboard-daily-chart__hit-area'
                    height={plotBottom - plotTop + 34}
                    key={`hit-${item.bucket}`}
                    onBlur={() => setHoveredBucket(null)}
                    onClick={() =>
                      onDrilldown({
                        mode: 'movements',
                        title: `Movimientos · ${label}`,
                        bucket: item.bucket,
                        granularity: timeline.granularity,
                      })
                    }
                    onFocus={() => setHoveredBucket(index)}
                    onKeyDown={(event) => {
                      if (event.key !== 'Enter' && event.key !== ' ') return
                      event.preventDefault()
                      onDrilldown({
                        mode: 'movements',
                        title: `Movimientos · ${label}`,
                        bucket: item.bucket,
                        granularity: timeline.granularity,
                      })
                    }}
                    onMouseEnter={() => setHoveredBucket(index)}
                    onMouseLeave={() => setHoveredBucket(null)}
                    role='button'
                    tabIndex={0}
                    width={slotWidth}
                    x={plotLeft + index * slotWidth}
                    y={plotTop}
                  />
                )
              })}
              {timeline.items.map((item, index) => (
                <text
                  className={`dashboard-daily-chart__label ${hoveredBucket === index ? 'is-highlighted' : ''}`}
                  key={item.bucket}
                  textAnchor='middle'
                  x={bucketCenter(index)}
                  y='291'
                >
                  {dayNumber(item.bucket)}
                </text>
              ))}
            </svg>
            {hoveredBucket !== null && timeline.items[hoveredBucket] ? (
              <div
                className='dashboard-daily-chart__tooltip'
                role='tooltip'
                style={{
                  left: `${Math.min(90, Math.max(10, (bucketCenter(hoveredBucket) / chartWidth) * 100))}%`,
                }}
              >
                <strong>
                  {bucketLabel(timeline.items[hoveredBucket].bucket, timeline.granularity)}
                </strong>
                {SERIES.map((series) => (
                  <span key={series.key}>
                    <i className={`dashboard-series-${series.key}`} />
                    {series.label}
                    <b>{formatCount(series.value(timeline.items[hoveredBucket]))}</b>
                  </span>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}
        {timeline && (!timeline.items.length || !hasActivity) ? (
          <div className='dashboard-chart-empty'>
            <Icon name='chart-bars' />
            <p>
              <strong>No hay evolución en el período</strong>
              <span>
                {hasActiveFilters
                  ? 'Probá restablecer o ampliar los filtros.'
                  : 'No hay actividad comercial en el período seleccionado.'}
              </span>
            </p>
          </div>
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

type ProvinceDonutItem = RankedItem & { province: string | null }

function ProvinceDonut({
  items,
  onSelect,
}: {
  items: ProvinceDonutItem[]
  onSelect: (province: string) => void
}) {
  const [highlightedIndex, setHighlightedIndex] = useState<number | null>(null)
  const total = items.reduce((sum, item) => sum + item.value, 0)
  let usedFraction = 0
  const activateWithKeyboard = (event: KeyboardEvent<SVGPathElement>, province: string) => {
    if (event.key !== 'Enter' && event.key !== ' ') return
    event.preventDefault()
    onSelect(province)
  }
  return (
    <div className='dashboard-province-donut-layout'>
      <div className='dashboard-province-donut-wrap'>
        <svg
          aria-label='Distribución de oportunidades creadas por provincia'
          className='dashboard-province-donut'
          viewBox='0 0 112 112'
        >
          <circle className='dashboard-province-donut__track' cx='56' cy='56' fill='none' r='44' />
          {items.map((item, index) => {
            const fraction = total ? item.value / total : 0
            if (item.value === 0) return null
            const startFraction = usedFraction
            usedFraction += fraction
            const percentage = Math.round(fraction * 100)
            const className = `dashboard-province-donut__segment dashboard-province-donut__segment--${index + 1} ${highlightedIndex === index ? 'is-highlighted' : ''}`
            const path = donutArcPath(startFraction, usedFraction)
            if (!item.province) {
              return (
                <path
                  aria-label={`${item.label}: ${item.displayValue}, ${percentage} %`}
                  className={className}
                  d={path}
                  data-share={fraction}
                  fill='none'
                  key={item.label}
                />
              )
            }
            const province = item.province
            return (
              // biome-ignore lint/a11y/useSemanticElements: SVG geometry cannot use a native HTML button; keyboard activation is implemented explicitly.
              <path
                aria-label={`${item.label}: ${item.displayValue}, ${percentage} %; abrir detalle`}
                className={className}
                d={path}
                data-share={fraction}
                fill='none'
                key={item.label}
                onBlur={() => setHighlightedIndex(null)}
                onClick={() => onSelect(province)}
                onFocus={() => setHighlightedIndex(index)}
                onKeyDown={(event) => activateWithKeyboard(event, province)}
                onMouseEnter={() => setHighlightedIndex(index)}
                onMouseLeave={() => setHighlightedIndex(null)}
                role='button'
                tabIndex={0}
              />
            )
          })}
        </svg>
        <div className='dashboard-province-donut__center'>
          <strong>{formatCount(total)}</strong>
          <span>creadas</span>
        </div>
      </div>
      <ul
        aria-label='Detalle de oportunidades creadas por provincia'
        className='dashboard-province-legend'
      >
        {items.map((item, index) => {
          const percentage = total ? Math.round((item.value / total) * 100) : 0
          const province = item.province
          const content = (
            <>
              <span
                aria-hidden='true'
                className={`dashboard-province-legend__dot dashboard-province-legend__dot--${index + 1}`}
              />
              <span className='dashboard-province-legend__identity'>
                <b>{item.label}</b>
                <small>{item.detail}</small>
              </span>
              <span className='dashboard-province-legend__metrics'>
                <b>{item.displayValue}</b>
                <small>{percentage} %</small>
              </span>
              {province ? <Icon name='chevron-right' /> : null}
            </>
          )
          return (
            <li key={item.label}>
              {province ? (
                <button
                  aria-label={`Ver oportunidades de ${item.label}`}
                  className={highlightedIndex === index ? 'is-highlighted' : undefined}
                  onBlur={() => setHighlightedIndex(null)}
                  onClick={() => onSelect(province)}
                  onFocus={() => setHighlightedIndex(index)}
                  onMouseEnter={() => setHighlightedIndex(index)}
                  onMouseLeave={() => setHighlightedIndex(null)}
                  type='button'
                >
                  {content}
                </button>
              ) : (
                <div>{content}</div>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function RankedBars({
  items,
  ariaLabel,
  onSelect,
  isSelectable,
}: {
  items: RankedItem[]
  ariaLabel: string
  onSelect?: (index: number) => void
  isSelectable?: (index: number) => boolean
}) {
  const maximum = Math.max(0, ...items.map((item) => item.value))
  return (
    <ol aria-label={ariaLabel} className='dashboard-ranked-bars'>
      {items.map((item, index) => (
        <li key={item.label}>
          {onSelect && (isSelectable?.(index) ?? true) ? (
            <button
              aria-label={`Ver oportunidades de ${item.label}`}
              className='dashboard-ranked-bars__action'
              onClick={() => onSelect(index)}
              type='button'
            >
              <span>
                <span>{item.label}</span>
                <b>{item.displayValue}</b>
              </span>
              <span aria-hidden='true' className='dashboard-ranked-bars__track'>
                <span style={{ width: `${maximum ? (item.value / maximum) * 100 : 0}%` }} />
              </span>
              <small>{item.detail}</small>
              <Icon name='chevron-right' />
            </button>
          ) : (
            <>
              <div>
                <span>{item.label}</span>
                <b>{item.displayValue}</b>
              </div>
              <div aria-hidden='true' className='dashboard-ranked-bars__track'>
                <span style={{ width: `${maximum ? (item.value / maximum) * 100 : 0}%` }} />
              </div>
              <small>{item.detail}</small>
            </>
          )}
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
  lossesSection,
  onRetry,
  onDrilldown,
}: {
  products?: ProductMetric[]
  sources?: SourceMetric[]
  provinces?: ProvinceMetric[]
  errors: { products?: string; sources?: string; provinces?: string }
  lossesSection: ReactNode
  onRetry: () => void
  hasActiveFilters: boolean
  onDrilldown: (selection: DrilldownSelection) => void
}) {
  const sourceTotal = sources?.reduce((sum, item) => sum + item.created, 0) ?? 0
  const orderedSources = sources ? [...sources].sort((a, b) => b.created - a.created) : undefined
  const sourceItems = orderedSources?.map((item) => ({
    label: sourceLabel(item.source),
    value: item.created,
    displayValue: formatCount(item.created),
    detail: sourceTotal
      ? `${Math.round((item.created / sourceTotal) * 100)} % de las creadas`
      : 'Sin oportunidades creadas',
  }))
  const orderedProducts = products
    ? [...products].sort((a, b) => Number(b.kg_quoted) - Number(a.kg_quoted))
    : undefined
  const productItems = orderedProducts?.map((item) => ({
    label: item.product_name,
    value: Number(item.kg_quoted),
    displayValue: formatDecimalKg(item.kg_quoted),
    detail: `${formatCount(item.opportunities_quoted)} oportunidades cotizadas`,
  }))
  const orderedProvinces = provinces
    ? [...provinces].sort((a, b) => b.opportunities_created - a.opportunities_created)
    : undefined
  const provinceItems = orderedProvinces?.map((item) => ({
    label: item.province ?? 'Sin provincia',
    value: item.opportunities_created,
    displayValue: formatCount(item.opportunities_created),
    detail: `${formatDecimalKg(item.kg_quoted)} cotizados`,
    province: item.province,
  }))
  return (
    <div className='dashboard-lower-analytics'>
      <section aria-labelledby='dashboard-origin-title' className='dashboard-origin'>
        <div className='dashboard-section-heading'>
          <div>
            <h2 id='dashboard-origin-title'>Origen de oportunidades</h2>
          </div>
          <Icon name='globe' />
        </div>
        <DistributionState error={errors.sources} items={sources} onRetry={onRetry}>
          {sourceItems ? (
            <RankedBars
              ariaLabel={sourceItems
                .map((item) => `${item.label}: ${item.displayValue}, ${item.detail}`)
                .join(', ')}
              items={sourceItems}
              onSelect={(index) =>
                onDrilldown({
                  title: `Oportunidades de origen ${sourceItems[index]?.label}`,
                  kind: 'created',
                  filters: {
                    source: orderedSources?.[index]?.source,
                  },
                })
              }
            />
          ) : null}
        </DistributionState>
      </section>
      <section aria-labelledby='dashboard-products-title' className='dashboard-secondary'>
        <div className='dashboard-section-heading'>
          <h2 id='dashboard-products-title'>Productos</h2>
          <Icon name='products' />
        </div>
        <DistributionState error={errors.products} items={productItems} onRetry={onRetry}>
          {productItems ? (
            <RankedBars
              ariaLabel={productItems
                .map((item) => `${item.label}: ${item.displayValue}`)
                .join(', ')}
              items={productItems.slice(0, 5)}
              onSelect={(index) =>
                onDrilldown({
                  title: `Oportunidades con ${productItems[index]?.label}`,
                  kind: 'created',
                  filters: { productId: orderedProducts?.[index]?.product_id },
                })
              }
            />
          ) : null}
        </DistributionState>
      </section>
      {lossesSection}
      <section
        aria-labelledby='dashboard-provinces-title'
        className='dashboard-secondary dashboard-provinces-wide'
      >
        <div className='dashboard-section-heading'>
          <h2 id='dashboard-provinces-title'>Provincias</h2>
          <Icon name='map-pin' />
        </div>
        <DistributionState error={errors.provinces} items={provinceItems} onRetry={onRetry}>
          {provinceItems ? (
            <ProvinceDonut
              items={provinceItems.slice(0, 5)}
              onSelect={(province) =>
                onDrilldown({
                  title: `Oportunidades de ${province}`,
                  kind: 'created',
                  filters: { province },
                })
              }
            />
          ) : null}
        </DistributionState>
      </section>
    </div>
  )
}

export function DashboardLosses({
  products,
  onDrilldown,
}: {
  products?: ProductMetric[]
  onDrilldown: (selection: DrilldownSelection) => void
}) {
  const losses =
    products
      ?.filter((item) => item.opportunities_lost > 0)
      .sort((a, b) => b.opportunities_lost - a.opportunities_lost) ?? []
  return (
    <section aria-labelledby='dashboard-losses-title' className='dashboard-losses'>
      <div className='dashboard-section-heading'>
        <div>
          <h2 id='dashboard-losses-title'>Pérdidas del período</h2>
          <p>Composición por producto al momento de la pérdida.</p>
        </div>
        {losses.length ? (
          <button
            className='dashboard-losses__analysis'
            onClick={() => onDrilldown({ title: 'Pérdidas del período', kind: 'lost' })}
            type='button'
          >
            Ver análisis <Icon name='chevron-right' />
          </button>
        ) : null}
      </div>
      {losses.length ? (
        <ul>
          {losses.map((item) => (
            <li key={item.product_id}>
              <button
                onClick={() =>
                  onDrilldown({
                    title: `Pérdidas · ${item.product_name}`,
                    kind: 'lost',
                    filters: { productId: item.product_id },
                  })
                }
                type='button'
              >
                <span>
                  <b>{item.product_name}</b>
                  <small>
                    {formatCount(item.opportunities_lost)} pérdidas ·{' '}
                    {formatDecimalKg(item.kg_lost)}
                  </small>
                </span>
                <Icon name='chevron-right' />
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className='dashboard-losses__empty'>
          <Icon name='check' />
          No hubo pérdidas en este período.
        </p>
      )}
    </section>
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
