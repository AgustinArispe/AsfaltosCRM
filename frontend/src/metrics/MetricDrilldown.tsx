import { useEffect, useRef, useState } from 'react'

import {
  getMetricOpportunities,
  getTimelineDayOpportunities,
  getTimelineMetrics,
} from '../api/metrics'
import type { ApiSession } from '../api/opportunities'
import {
  LOSS_REASON_LABELS,
  OPPORTUNITY_STATUS_LABELS,
  opportunityStatusColorClass,
} from '../pipeline/config'
import type { LeadSource, LossReason, OpportunityStatus } from '../pipeline/types'
import { navigateRoute } from '../routing/router'
import { formatDecimalKg } from '../shared/formatters'
import { Icon } from '../shared/Icon'
import { Modal } from '../shared/Modal'
import { sourceLabel } from './filters'
import type {
  MetricOpportunities,
  MetricOpportunityKind,
  MetricsFilters,
  TimelineDayOpportunities,
  TimelineGranularity,
  TimelineMetric,
  TimelineMetrics,
  TimelineSeries,
} from './types'

type OpportunitySelection = {
  mode?: 'opportunities'
  title: string
  kind: MetricOpportunityKind
  status?: OpportunityStatus
  filters?: Partial<MetricsFilters>
}

type MovementSelection = {
  mode: 'movements'
  title: string
  bucket: string
  granularity: TimelineGranularity
}

export type DrilldownSelection = OpportunitySelection | MovementSelection
type DaySelection = { bucket: string; series: TimelineSeries }

const DATE_FORMATTER = new Intl.DateTimeFormat('es-AR', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  timeZone: 'America/Argentina/Buenos_Aires',
})
const DAY_FORMATTER = new Intl.DateTimeFormat('es-AR', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  timeZone: 'America/Argentina/Buenos_Aires',
})
const SHORT_DAY_FORMATTER = new Intl.DateTimeFormat('es-AR', {
  day: 'numeric',
  month: 'long',
  timeZone: 'America/Argentina/Buenos_Aires',
})
const SERIES_COPY: Record<
  TimelineSeries,
  { label: string; singular: string; icon: 'document' | 'check' | 'x-circle' }
> = {
  created: { label: 'Creadas', singular: 'creada', icon: 'document' },
  won: { label: 'Ganadas', singular: 'ganada', icon: 'check' },
  lost: { label: 'Pérdidas', singular: 'pérdida', icon: 'x-circle' },
}

function localDate(value: string): Date {
  return new Date(`${value.slice(0, 10)}T12:00:00-03:00`)
}
function formatDate(value: string): string {
  return DATE_FORMATTER.format(localDate(value)).replaceAll(' de ', ' ').replace('.', '')
}
function formatDay(value: string): string {
  const text = DAY_FORMATTER.format(localDate(value)).replaceAll(' de ', ' ')
  return `${text.charAt(0).toLocaleUpperCase('es-AR')}${text.slice(1)}`
}
function formatShortDay(value: string): string {
  return SHORT_DAY_FORMATTER.format(localDate(value)).replaceAll(' de ', ' ')
}
function addDays(value: string, days: number): string {
  const [year, month, day] = value.slice(0, 10).split('-').map(Number)
  return new Date(Date.UTC(year, month - 1, day + days)).toISOString().slice(0, 10)
}
function nextMonth(value: string): string {
  const [year, month] = value.slice(0, 10).split('-').map(Number)
  return new Date(Date.UTC(year, month, 1)).toISOString().slice(0, 10)
}
function bucketFilters(filters: MetricsFilters, selection: MovementSelection): MetricsFilters {
  const start = selection.bucket.slice(0, 10)
  const rawEnd =
    selection.granularity === 'day'
      ? addDays(start, 1)
      : selection.granularity === 'week'
        ? addDays(start, 7)
        : nextMonth(start)
  const from = start > filters.from.slice(0, 10) ? start : filters.from.slice(0, 10)
  const to = rawEnd < filters.to.slice(0, 10) ? rawEnd : filters.to.slice(0, 10)
  return { ...filters, from: `${from}T00:00:00-03:00`, to: `${to}T00:00:00-03:00` }
}
function movementValue(item: TimelineMetric, series: TimelineSeries): number {
  return series === 'created' ? item.leads_created : item[series]
}
function hasCommercialQuantity(value: string): boolean {
  return !/^0+(?:\.0+)?$/.test(value)
}

function sumDecimalKg(values: string[]): string | undefined {
  if (values.length === 0) return undefined
  const parts = values.map((value) => value.split('.'))
  const scale = Math.max(0, ...parts.map(([, fraction = '']) => fraction.length))
  const factor = 10n ** BigInt(scale)
  const total = parts.reduce((sum, [whole = '0', fraction = '']) => {
    return sum + BigInt(whole) * factor + BigInt(fraction.padEnd(scale, '0') || '0')
  }, 0n)
  if (scale === 0) return total.toString()
  return `${total / factor}.${(total % factor).toString().padStart(scale, '0')}`
}

function OpportunityCard({
  item,
  relevantAt,
  quantityKg,
  lossReason,
}: {
  item: {
    opportunity_id: number
    loss_event_id: number | null
    customer_name: string
    customer_company: string | null
    current_status: OpportunityStatus
    source: LeadSource
  }
  relevantAt?: string
  quantityKg?: string
  lossReason?: string | null
}) {
  return (
    <button
      aria-label={`Abrir oportunidad ${item.opportunity_id} de ${item.customer_name}`}
      className={`metric-drilldown__card ${opportunityStatusColorClass(item.current_status)}`}
      onClick={() =>
        navigateRoute(
          { kind: 'opportunity', opportunityId: item.opportunity_id, surface: 'pipeline' },
          { origin: { kind: 'workspace', workspace: 'dashboard' } },
        )
      }
      type='button'
    >
      <span className='metric-drilldown__icon'>
        <Icon name='document' />
      </span>
      <span className='metric-drilldown__content'>
        <span className='metric-drilldown__identity'>
          <strong>{item.customer_company ?? item.customer_name}</strong>
          {item.customer_company ? <small>{item.customer_name}</small> : null}
        </span>
        <span className='metric-drilldown__commercial'>
          <span className='metric-drilldown__status'>
            {OPPORTUNITY_STATUS_LABELS[item.current_status]}
          </span>
          {quantityKg && hasCommercialQuantity(quantityKg) ? (
            <b>{formatDecimalKg(quantityKg)}</b>
          ) : null}
        </span>
        {lossReason ? (
          <span className='metric-drilldown__loss-reason'>
            {LOSS_REASON_LABELS[lossReason as LossReason]}
          </span>
        ) : null}
        <span className='metric-drilldown__meta'>
          <span>
            #{item.opportunity_id} · {sourceLabel(item.source)}
          </span>
          {relevantAt ? <time dateTime={relevantAt}>{formatDate(relevantAt)}</time> : null}
        </span>
      </span>
      <Icon className='metric-drilldown__chevron' name='chevron-right' />
    </button>
  )
}

export function MetricDrilldown({
  filters,
  selection,
  session,
  onClose,
}: {
  filters: MetricsFilters
  selection: DrilldownSelection | null
  session: ApiSession
  onClose: () => void
}) {
  const [metricData, setMetricData] = useState<MetricOpportunities | null>(null)
  const [movementData, setMovementData] = useState<TimelineMetrics | null>(null)
  const [dayData, setDayData] = useState<TimelineDayOpportunities | null>(null)
  const [daySelection, setDaySelection] = useState<DaySelection | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const displayedSelectionRef = useRef<DrilldownSelection | null>(selection)
  const backButtonRef = useRef<HTMLButtonElement>(null)
  const movementTriggerRef = useRef<HTMLButtonElement | null>(null)
  const displayedSelection = selection ?? displayedSelectionRef.current

  useEffect(() => {
    if (selection) displayedSelectionRef.current = selection
  }, [selection])
  useEffect(() => {
    if (!selection) return
    const controller = new AbortController()
    setMetricData(null)
    setMovementData(null)
    setDayData(null)
    setDaySelection(null)
    setError(null)
    setIsLoading(true)
    const request =
      selection.mode === 'movements'
        ? getTimelineMetrics(bucketFilters(filters, selection), 'day', {
            ...session,
            signal: controller.signal,
          }).then(setMovementData)
        : getMetricOpportunities(
            { ...filters, ...selection.filters },
            selection.kind,
            selection.status ?? null,
            1,
            { ...session, signal: controller.signal },
          ).then(setMetricData)
    request
      .catch(() => {
        if (!controller.signal.aborted) setError('No pudimos cargar este detalle.')
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false)
      })
    return () => controller.abort()
  }, [filters, selection, session])
  useEffect(() => {
    if (daySelection) backButtonRef.current?.focus()
  }, [daySelection])

  const loadMetricPage = async (page: number) => {
    if (!selection || selection.mode === 'movements' || page < 1) return
    setIsLoading(true)
    setError(null)
    try {
      setMetricData(
        await getMetricOpportunities(
          { ...filters, ...selection.filters },
          selection.kind,
          selection.status ?? null,
          page,
          session,
        ),
      )
    } catch {
      setError('No pudimos cargar esta página de oportunidades.')
    } finally {
      setIsLoading(false)
    }
  }
  const loadDayPage = async (day: DaySelection, page: number) => {
    setDaySelection(day)
    setDayData(null)
    setError(null)
    setIsLoading(true)
    try {
      setDayData(await getTimelineDayOpportunities(filters, day.bucket, day.series, page, session))
    } catch {
      setError('No pudimos cargar las oportunidades de este movimiento.')
    } finally {
      setIsLoading(false)
    }
  }
  const returnToMovements = () => {
    setDaySelection(null)
    setDayData(null)
    setError(null)
    window.requestAnimationFrame(() => movementTriggerRef.current?.focus())
  }

  const meaningfulDays =
    movementData?.items.filter((item) =>
      (['created', 'won', 'lost'] as const).some((series) => movementValue(item, series) > 0),
    ) ?? []
  const pageData = daySelection ? dayData : metricData
  const totalPages = pageData ? Math.max(1, Math.ceil(pageData.total / pageData.page_size)) : 1
  const title = daySelection
    ? `${SERIES_COPY[daySelection.series].label} · ${formatShortDay(daySelection.bucket)}`
    : (displayedSelection?.title ?? 'Detalle')
  const description = daySelection
    ? dayData
      ? `${dayData.total} ${dayData.total === 1 ? 'oportunidad' : 'oportunidades'}`
      : 'Oportunidades que componen el movimiento'
    : displayedSelection?.mode === 'movements'
      ? meaningfulDays.length
        ? `${meaningfulDays.length} días con actividad`
        : 'Detalle diario del período'
      : metricData
        ? `${metricData.total} ${metricData.total === 1 ? 'oportunidad' : 'oportunidades'}`
        : 'Detalle del período y filtros aplicados'

  return (
    <Modal
      contentClassName='dashboard-modal-panel'
      description={description}
      initialFocusClose={!daySelection}
      isOpen={Boolean(selection)}
      onClose={onClose}
      renderHeader={
        daySelection
          ? ({ titleId, descriptionId }) => (
              <div className='dashboard-modal-heading'>
                <button
                  aria-label='Volver a movimientos'
                  className='dashboard-modal-back'
                  onClick={returnToMovements}
                  ref={backButtonRef}
                  type='button'
                >
                  <Icon name='chevron-left' />
                  <span>Volver a movimientos</span>
                </button>
                <div>
                  <h2 id={titleId}>{title}</h2>
                  <p id={descriptionId}>{description}</p>
                </div>
              </div>
            )
          : undefined
      }
      size='dashboard'
      title={title}
    >
      <div aria-busy={isLoading} className='metric-drilldown'>
        {isLoading && !pageData && !movementData ? <p role='status'>Cargando detalle…</p> : null}
        {error ? (
          <p className='dashboard-surface-error' role='alert'>
            {error}
          </p>
        ) : null}

        {displayedSelection?.mode === 'movements' && !daySelection ? (
          <div className='dashboard-movements'>
            {movementData && meaningfulDays.length === 0 ? (
              <p className='dashboard-compact-empty'>No hubo movimientos en este período.</p>
            ) : null}
            {meaningfulDays.map((day) => (
              <section className='dashboard-movement-day' key={day.bucket}>
                <h3>{formatDay(day.bucket)}</h3>
                <div>
                  {(['created', 'won', 'lost'] as const).map((series) => {
                    const count = movementValue(day, series)
                    if (count === 0) return null
                    const copy = SERIES_COPY[series]
                    return (
                      <button
                        className={`dashboard-movement-button dashboard-movement-button--${series}`}
                        key={series}
                        onClick={(event) => {
                          movementTriggerRef.current = event.currentTarget
                          void loadDayPage({ bucket: day.bucket, series }, 1)
                        }}
                        type='button'
                      >
                        <Icon name={copy.icon} />
                        <span>
                          {count}{' '}
                          {count === 1 ? copy.singular : copy.label.toLocaleLowerCase('es-AR')}
                        </span>
                        <Icon name='chevron-right' />
                      </button>
                    )
                  })}
                </div>
              </section>
            ))}
          </div>
        ) : null}

        {displayedSelection?.mode !== 'movements' && metricData?.items.length === 0 ? (
          <p className='dashboard-compact-empty'>No hay oportunidades para este indicador.</p>
        ) : null}
        {daySelection && dayData?.items.length === 0 ? (
          <p className='dashboard-compact-empty'>No hay oportunidades para este movimiento.</p>
        ) : null}
        {pageData?.items.length ? (
          <ul aria-label={title} className='metric-drilldown__grid'>
            {pageData.items.map((item) => (
              <li key={`${item.opportunity_id}-${item.loss_event_id ?? 'current'}`}>
                <OpportunityCard
                  item={item}
                  lossReason={'loss_reason' in item ? item.loss_reason : undefined}
                  quantityKg={
                    'quantity_kg' in item
                      ? item.quantity_kg
                      : sumDecimalKg(item.products.map((product) => product.quantity_kg))
                  }
                  relevantAt={'relevant_at' in item ? item.relevant_at : daySelection?.bucket}
                />
              </li>
            ))}
          </ul>
        ) : null}
        {pageData && totalPages > 1 ? (
          <footer className='metric-drilldown__pagination'>
            <span>
              Página {pageData.page} de {totalPages}
            </span>
            <div>
              <button
                aria-label='Página anterior'
                className='metric-drilldown__page-button'
                disabled={isLoading || pageData.page <= 1}
                onClick={() =>
                  daySelection
                    ? void loadDayPage(daySelection, pageData.page - 1)
                    : void loadMetricPage(pageData.page - 1)
                }
                type='button'
              >
                <Icon name='chevron-left' />
              </button>
              <button
                aria-label='Página siguiente'
                className='metric-drilldown__page-button'
                disabled={isLoading || pageData.page >= totalPages}
                onClick={() =>
                  daySelection
                    ? void loadDayPage(daySelection, pageData.page + 1)
                    : void loadMetricPage(pageData.page + 1)
                }
                type='button'
              >
                <Icon name='chevron-right' />
              </button>
            </div>
          </footer>
        ) : null}
      </div>
    </Modal>
  )
}
