import { type MouseEvent, useEffect, useMemo, useRef, useState } from 'react'
import { getLostFilterOptions, getLostStatistics, listLostOpportunities } from '../api/lost'
import type { ApiSession } from '../api/opportunities'
import { useAuth } from '../auth/AuthContext'
import { LossRecommendation } from '../lost/LossRecommendation'
import {
  EMPTY_LOST_FILTERS,
  type LostFilters,
  type LostOpportunity,
  type LostStatistics,
} from '../lost/types'
import {
  LOSS_REASON_LABELS,
  LOSS_REASON_OPTIONS,
  OPPORTUNITY_STATUS_LABELS,
  SOURCE_LABELS,
} from '../pipeline/config'
import { isLeadSource, type LossReason } from '../pipeline/types'
import { AppLink } from '../routing/router'
import { Button } from '../shared/Button'
import { ClosedOpportunityFilters } from '../shared/ClosedOpportunityFilters'
import { donutArcPath } from '../shared/donut'
import { formatDateTime, formatDecimalKg } from '../shared/formatters'
import { Icon } from '../shared/Icon'
import { isPeriodPreset, periodSelection, validDateRange } from '../shared/periods'
import { SegmentedControl } from '../shared/SegmentedControl'
import { EmptyState, InlineFeedback, WorkspaceSkeleton } from '../shared/StatusStates'
import type { WonFilterOptions } from '../won/types'
import { OpportunityDetailPage } from './OpportunityDetailPage'

function defaultFilters(): LostFilters {
  const { from, to } = periodSelection('month')
  return { ...EMPTY_LOST_FILTERS, period: 'month', from, to }
}

function readLostFilters(): LostFilters {
  const query = new URLSearchParams(window.location.search)
  const source = query.get('source')
  const requestedPeriod = query.get('period')
  const period = isPeriodPreset(requestedPeriod)
    ? requestedPeriod
    : query.has('from') || query.has('to')
      ? 'custom'
      : 'month'
  const dates = periodSelection(period === 'custom' ? 'all' : period)
  const readId = (key: string) => {
    const value = query.get(key) ?? ''
    return /^[1-9]\d*$/.test(value) && Number.isSafeInteger(Number(value)) ? value : ''
  }
  const readDate = (key: string, fallback: string) => {
    const value = query.get(key)
    return value && validDateRange(value, value) ? value : fallback
  }
  return {
    ...EMPTY_LOST_FILTERS,
    period,
    search: query.get('search') ?? '',
    source: isLeadSource(source) ? source : '',
    product: readId('product'),
    customerId: Number(readId('customer')) || null,
    province: query.get('province') ?? '',
    responsible: query.get('unassigned') === 'true' ? '' : readId('responsible'),
    unassigned: query.get('unassigned') === 'true',
    reasons: LOSS_REASON_OPTIONS.filter((option) =>
      query.getAll('reason').includes(option.value),
    ).map((option) => option.value),
    from: period === 'all' ? '' : readDate('from', dates.from),
    to: period === 'all' ? '' : readDate('to', dates.to),
  }
}

const LOST_RESULT_VIEWS = [
  { value: 'table', label: 'Tabla' },
  { value: 'cards', label: 'Fichas' },
] as const
type LostResultView = (typeof LOST_RESULT_VIEWS)[number]['value']

function setResultViewQuery(query: URLSearchParams, view: LostResultView) {
  if (view === 'cards') query.set('vista', 'fichas')
  else query.delete('vista')
  window.history.replaceState(window.history.state, '', query.size ? `/lost?${query}` : '/lost')
}

function replaceLostQuery(filters: LostFilters, view: LostResultView): void {
  const query = new URLSearchParams()
  for (const key of [
    'period',
    'from',
    'to',
    'search',
    'source',
    'product',
    'province',
    'responsible',
  ] as const) {
    if (filters[key]) query.set(key, filters[key])
  }
  for (const reason of filters.reasons) query.append('reason', reason)
  if (filters.unassigned) query.set('unassigned', 'true')
  if (filters.customerId) query.set('customer', String(filters.customerId))
  setResultViewQuery(query, view)
}

function lostDetailLink(opportunityId: number, onOpen: (id: number) => void) {
  return {
    onClick: (event: MouseEvent<HTMLAnchorElement>) => {
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey)
        return
      event.preventDefault()
      onOpen(opportunityId)
    },
    origin: { kind: 'workspace', workspace: 'lost' } as const,
    search: window.location.search,
    to: { kind: 'opportunity', opportunityId, surface: 'lost' } as const,
  }
}

function lostProducts(item: LostOpportunity) {
  const names = item.loss_products
    .slice(0, 2)
    .map((product) => product.product_name)
    .join(', ')
  const remaining = item.loss_products.length - 2
  return remaining > 0 ? `${names} +${remaining}` : names
}

function LostReasonLabel({ reason }: { reason: LossReason }) {
  return (
    <span className='lost-reason-label'>
      <span aria-hidden='true' className='lost-reason-dot' data-loss-reason={reason} />
      <strong>{LOSS_REASON_LABELS[reason]}</strong>
    </span>
  )
}

function LostCards({ items, onOpen }: { items: LostOpportunity[]; onOpen: (id: number) => void }) {
  return (
    <ul
      aria-label='Fichas de oportunidades perdidas'
      className='won-results__list closed-card-list'
    >
      {items.map((item) => {
        const { opportunity } = item
        const products = lostProducts(item)
        return (
          <li key={item.loss_event_id}>
            <AppLink
              {...lostDetailLink(opportunity.id, onOpen)}
              className='won-result-card lost-result-card'
            >
              <span className='won-result-card__icon lost-result-card__icon'>
                <Icon name='x-circle' />
              </span>
              <span className='won-result-card__customer lost-result-card__customer'>
                <strong>{opportunity.customer.name}</strong>
                {opportunity.customer.company ? <span>{opportunity.customer.company}</span> : null}
              </span>
              <span className='lost-result-card__reason'>
                <LostReasonLabel reason={item.loss_reason} />
                {item.loss_reason_detail ? (
                  <span className='lost-reason-detail'>{item.loss_reason_detail}</span>
                ) : null}
                {item.from_status ? (
                  <small>Desde {OPPORTUNITY_STATUS_LABELS[item.from_status]}</small>
                ) : null}
              </span>
              <span className='won-result-card__quantity lost-result-card__quote'>
                {products ? (
                  <>
                    <strong>{formatDecimalKg(item.quoted_total_kg)}</strong>
                    <small>{products}</small>
                  </>
                ) : (
                  <small>Sin cotización</small>
                )}
              </span>
              <span className='lost-result-card__context'>
                <time dateTime={item.lost_at}>{formatDateTime(item.lost_at)}</time>
                <small>
                  {SOURCE_LABELS[opportunity.source]}
                  {item.customer_province ? ` · ${item.customer_province}` : ''}
                </small>
                {opportunity.assigned_user ? (
                  <small>{opportunity.assigned_user.full_name}</small>
                ) : null}
                {opportunity.is_reopened ? <small>Reabierta previamente</small> : null}
              </span>
              <Icon
                className='won-result-card__chevron lost-result-card__arrow'
                name='chevron-right'
              />
            </AppLink>
          </li>
        )
      })}
    </ul>
  )
}

function LostRows({ items, onOpen }: { items: LostOpportunity[]; onOpen: (id: number) => void }) {
  return (
    <div className='closed-history-table'>
      <table className='w-full min-w-[50rem] border-collapse text-left text-sm'>
        <caption className='sr-only'>Oportunidades actualmente perdidas</caption>
        <thead>
          <tr className='closed-history-table__heading border-b border-[var(--border-default)] text-xs text-[var(--text-secondary)]'>
            <th className='px-4 py-3 font-semibold' scope='col'>
              Cliente
            </th>
            <th className='px-4 py-3 font-semibold' scope='col'>
              Motivo de pérdida
            </th>
            <th className='px-4 py-3 font-semibold' scope='col'>
              Cotización
            </th>
            <th className='px-4 py-3 font-semibold' scope='col'>
              Fecha de pérdida
            </th>
            <th className='px-3 py-3' scope='col'>
              <span className='sr-only'>Abrir</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const { opportunity } = item
            const [lossDate, lossTime] = formatDateTime(item.lost_at).split(', ')
            const link = lostDetailLink(opportunity.id, onOpen)
            return (
              <tr
                className='closed-history-table__row border-b border-[var(--border-subtle)] last:border-b-0'
                key={item.loss_event_id}
              >
                <th className='closed-history-table__customer px-4 py-3 font-semibold' scope='row'>
                  <AppLink
                    {...link}
                    aria-label={opportunity.customer.name}
                    className='closed-history-table__customer-link outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]'
                  >
                    <span>
                      {opportunity.customer.name}
                      {opportunity.customer.company ? (
                        <span className='block text-xs font-normal text-[var(--text-secondary)]'>
                          {opportunity.customer.company}
                        </span>
                      ) : null}
                    </span>
                  </AppLink>
                  <span className='block text-xs font-normal text-[var(--text-secondary)]'>
                    {SOURCE_LABELS[opportunity.source]}
                    {item.customer_province ? ` · ${item.customer_province}` : ''}
                  </span>
                  {opportunity.assigned_user ? (
                    <span className='block text-xs font-normal text-[var(--text-secondary)]'>
                      {opportunity.assigned_user.full_name}
                    </span>
                  ) : null}
                </th>
                <td className='closed-history-table__breakdown px-4 py-3'>
                  <LostReasonLabel reason={item.loss_reason} />
                  {item.loss_reason_detail ? (
                    <span className='lost-reason-detail'>{item.loss_reason_detail}</span>
                  ) : null}
                  {item.from_status ? (
                    <span className='mt-1 block text-xs text-[var(--text-secondary)]'>
                      Desde {OPPORTUNITY_STATUS_LABELS[item.from_status]}
                    </span>
                  ) : null}
                </td>
                <td className='closed-history-table__quote px-4 py-3'>
                  {item.loss_products.length ? (
                    <>
                      <strong className='block tabular-nums text-[var(--brand-deep)]'>
                        {formatDecimalKg(item.quoted_total_kg)}
                      </strong>
                      <span className='mt-0.5 block text-xs'>{lostProducts(item)}</span>
                    </>
                  ) : (
                    'Sin cotización'
                  )}
                </td>
                <td className='closed-history-table__date px-4 py-3'>
                  <time dateTime={item.lost_at}>
                    <strong className='block font-semibold text-[var(--text-primary)]'>
                      {lossDate}
                    </strong>
                    <span>{lossTime}</span>
                  </time>
                  {opportunity.is_reopened ? (
                    <span className='mt-1 block text-xs'>Reabierta previamente</span>
                  ) : null}
                </td>
                <td className='px-3 py-3 text-right'>
                  <AppLink
                    {...link}
                    aria-label={`Abrir oportunidad ${opportunity.id} de ${opportunity.customer.name}`}
                    className='closed-history-table__open inline-flex size-11 items-center justify-center rounded-[var(--radius-control)] focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]'
                  >
                    <Icon className='size-4' name='chevron-right' />
                  </AppLink>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

const formatShare = new Intl.NumberFormat('es-AR', { style: 'percent', maximumFractionDigits: 1 })
const formatCount = new Intl.NumberFormat('es-AR')
const LOSS_MEASURES = [
  { value: 'count', label: 'Por casos' },
  { value: 'kg', label: 'Por kilos' },
] as const
type LossMeasure = (typeof LOSS_MEASURES)[number]['value']

function LossAnalysis({
  statistics,
  activeReasons,
  measure,
  onMeasure,
  onReason,
}: {
  statistics: LostStatistics
  activeReasons: LossReason[]
  measure: LossMeasure
  onMeasure: (measure: LossMeasure) => void
  onReason: (reason: LossReason) => void
}) {
  const byKg = measure === 'kg'
  const total = byKg ? Number(statistics.current_quantity_kg) : statistics.current_count
  const chartTotal = byKg
    ? formatDecimalKg(statistics.current_quantity_kg).replace(/ kg$/, '')
    : formatCount.format(statistics.current_count)
  const rankByKg = byKg && total > 0
  const reasons = statistics.current_by_reason
    .map((reason) => ({
      ...reason,
      value: byKg ? Number(reason.quantity_kg) : reason.count,
    }))
    .sort((left, right) => (rankByKg ? right.value - left.value : right.count - left.count))
  let offset = 0
  const segments = reasons.map((reason) => {
    const share = total > 0 ? reason.value / total : 0
    const start = offset
    offset += share
    const gap = share >= 1 ? 0 : Math.min(share * 0.15, 0.006)
    return {
      ...reason,
      share,
      path: share > 0 ? donutArcPath(start + gap / 2, offset - gap / 2) : null,
    }
  })
  return (
    <>
      <section aria-labelledby='closed-summary-title' className='closed-summary'>
        <header className='closed-section-header closed-summary__header'>
          <h2 id='closed-summary-title'>Resumen de pérdidas</h2>
          <dl className='closed-summary__metrics'>
            <div>
              <dt>Kg cotizados perdidos</dt>
              <dd>{formatDecimalKg(statistics.current_quantity_kg)}</dd>
            </div>
            <div>
              <dt>Sin cotización</dt>
              <dd>{formatCount.format(statistics.without_quote_count)}</dd>
            </div>
          </dl>
        </header>
        <section aria-labelledby='lost-reasons-title' className='lost-insight'>
          <div className='lost-insight__header'>
            <h3 id='lost-reasons-title'>Motivos de pérdida</h3>
            {reasons.length ? (
              <SegmentedControl
                label='Medida de los motivos de pérdida'
                onChange={(value) => onMeasure(value === 'kg' ? 'kg' : 'count')}
                segments={LOSS_MEASURES}
                value={measure}
              />
            ) : null}
          </div>
          {reasons.length ? (
            <div className='lost-reason-breakdown'>
              <div className='outcome-donut'>
                <svg aria-hidden='true' viewBox='0 0 112 112'>
                  <circle className='outcome-donut__track' cx='56' cy='56' r='44' />
                  {segments.map((segment) =>
                    segment.path ? (
                      <path
                        className='lost-donut__segment'
                        d={segment.path}
                        data-loss-reason={segment.key}
                        key={segment.key}
                      />
                    ) : null,
                  )}
                </svg>
                <div className='outcome-donut__center'>
                  <strong
                    className={chartTotal.length > 8 ? 'outcome-donut__wide-total' : undefined}
                  >
                    {chartTotal}
                  </strong>
                  <span>
                    {byKg
                      ? 'kg cotizados'
                      : statistics.current_count === 1
                        ? 'pérdida'
                        : 'pérdidas'}
                  </span>
                </div>
              </div>
              <div className='lost-reason-legend'>
                <div aria-hidden='true' className='lost-reason-columns lost-insight-columns'>
                  <span>Motivo</span>
                  <span>{byKg ? 'Cotizados' : 'Casos'}</span>
                  <span>% total</span>
                </div>
                <ul>
                  {segments.map((reason) => (
                    <li key={reason.key}>
                      <button
                        aria-pressed={activeReasons.includes(reason.key)}
                        className='lost-reason-row lost-reason-columns'
                        onClick={() => onReason(reason.key)}
                        type='button'
                      >
                        <LostReasonLabel reason={reason.key} />
                        <span className='lost-insight-figure'>
                          {byKg
                            ? formatDecimalKg(reason.quantity_kg)
                            : formatCount.format(reason.count)}
                          {!byKg ? (
                            <span className='sr-only'>
                              {reason.count === 1 ? ' caso' : ' casos'}
                            </span>
                          ) : null}
                        </span>
                        <span className='lost-insight-figure'>
                          {reason.share > 0 && reason.share < 0.001
                            ? '<0,1%'
                            : formatShare.format(reason.share)}
                          <span className='sr-only'> del total</span>
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
                {total === 0 ? (
                  <p className='lost-insight__empty'>No hay kilos cotizados en estas pérdidas.</p>
                ) : null}
              </div>
            </div>
          ) : (
            <p className='lost-insight__empty'>Sin motivos en las pérdidas filtradas.</p>
          )}
        </section>
        {statistics.reopened_count > 0 ||
        statistics.historical_loss_count !== statistics.current_count ? (
          <p className='closed-summary__history'>
            Histórico del período · {statistics.historical_loss_count}{' '}
            {statistics.historical_loss_count === 1 ? 'cierre registrado' : 'cierres registrados'} ·{' '}
            {statistics.reopened_count}{' '}
            {statistics.reopened_count === 1 ? 'reapertura' : 'reaperturas'}
          </p>
        ) : null}
      </section>
      <LossRecommendation
        reasons={reasons.map(({ key, count, value }) => ({ key, value: rankByKg ? value : count }))}
      />
    </>
  )
}

export function LostPage({ selectedOpportunityId }: { selectedOpportunityId?: number }) {
  const { token, logout } = useAuth()
  const session = useMemo<ApiSession>(
    () => ({ token: token ?? '', onUnauthorized: logout }),
    [logout, token],
  )
  const [draft, setDraft] = useState<LostFilters>(readLostFilters)
  const [filters, setFilters] = useState<LostFilters>(draft)
  const [items, setItems] = useState<LostOpportunity[]>([])
  const [nextCursor, setNextCursor] = useState<string | null>(null)
  const [measure, setMeasure] = useState<LossMeasure>('count')
  const [resultView, setResultView] = useState<LostResultView>(() =>
    new URLSearchParams(window.location.search).get('vista') === 'fichas' ? 'cards' : 'table',
  )
  const [statistics, setStatistics] = useState<LostStatistics | null>(null)
  const [options, setOptions] = useState<WonFilterOptions | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pageError, setPageError] = useState<string | null>(null)
  const [filterError, setFilterError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [openOpportunityId, setOpenOpportunityId] = useState<number | null>(null)
  const controllerRef = useRef<AbortController | null>(null)
  const activeOpportunityId = selectedOpportunityId ?? openOpportunityId

  useEffect(() => {
    void reloadKey
    const controller = new AbortController()
    getLostFilterOptions({ ...session, signal: controller.signal })
      .then((value) => {
        if (!controller.signal.aborted) setOptions(value)
      })
      .catch(() => undefined)
    return () => controller.abort()
  }, [session, reloadKey])

  useEffect(() => {
    void reloadKey
    const controller = new AbortController()
    controllerRef.current = controller
    setLoading(true)
    setLoadingMore(false)
    setError(null)
    setPageError(null)
    const requestSession = { ...session, signal: controller.signal }
    Promise.all([
      listLostOpportunities(filters, null, requestSession),
      getLostStatistics(filters, requestSession),
    ])
      .then(([page, summary]) => {
        if (controller.signal.aborted) return
        setItems(page.items)
        setNextCursor(page.next_cursor)
        setStatistics(summary)
      })
      .catch(() => {
        if (!controller.signal.aborted) setError('No pudimos cargar las oportunidades perdidas.')
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [filters, reloadKey, session])

  const apply = (next: LostFilters) => {
    if (next.from && next.to && next.from > next.to) {
      setFilterError('La fecha Hasta tiene que ser igual o posterior a Desde.')
      return
    }
    setFilterError(null)
    const normalized = { ...next, search: next.search.trim() }
    replaceLostQuery(normalized, resultView)
    setDraft(normalized)
    setFilters(normalized)
  }
  const reset = () => {
    const next = defaultFilters()
    setResultViewQuery(new URLSearchParams(), resultView)
    setFilterError(null)
    setDraft(next)
    setFilters(next)
  }
  const loadMore = async () => {
    const controller = controllerRef.current
    if (!nextCursor || !controller || loadingMore) return
    setLoadingMore(true)
    setPageError(null)
    try {
      const page = await listLostOpportunities(filters, nextCursor, {
        ...session,
        signal: controller.signal,
      })
      if (controller.signal.aborted) return
      setItems((current) => [...current, ...page.items])
      setNextCursor(page.next_cursor)
    } catch {
      if (!controller.signal.aborted) setPageError('No pudimos cargar más oportunidades perdidas.')
    } finally {
      if (!controller.signal.aborted) setLoadingMore(false)
    }
  }
  const activeExtraFilters =
    filters.reasons.length +
    [
      filters.product,
      filters.source,
      filters.province,
      filters.responsible || filters.unassigned,
      filters.customerId,
    ].filter(Boolean).length
  const filtered = filters.period !== 'all' || activeExtraFilters > 0 || Boolean(filters.search)

  return (
    <section
      aria-label='Oportunidades perdidas'
      className='won-workspace lost-workspace mx-auto w-full min-w-0 max-w-[90rem]'
    >
      <ClosedOpportunityFilters
        activeExtraFilters={activeExtraFilters}
        apply={() => apply(draft)}
        draft={draft}
        label='Filtrar Perdidas'
        options={options}
        resetFilters={reset}
        setDraft={setDraft}
        surface='lost'
      >
        <fieldset className='lost-reason-filters'>
          <legend className='ui-label'>Motivo de pérdida</legend>
          <div className='flex flex-wrap gap-2'>
            {LOSS_REASON_OPTIONS.map((option) => (
              <label className='lost-reason-filter' key={option.value}>
                <input
                  checked={draft.reasons.includes(option.value)}
                  onChange={(event) => {
                    const checked = event.currentTarget.checked
                    setDraft((current) => ({
                      ...current,
                      reasons: checked
                        ? [...current.reasons, option.value]
                        : current.reasons.filter((reason) => reason !== option.value),
                    }))
                  }}
                  type='checkbox'
                />
                {option.label}
              </label>
            ))}
          </div>
        </fieldset>
      </ClosedOpportunityFilters>
      {filterError ? <InlineFeedback message={filterError} /> : null}
      {loading ? (
        <WorkspaceSkeleton label='Cargando pérdidas' />
      ) : error ? (
        <div className='ui-panel p-5'>
          <InlineFeedback message={error} />
          <Button className='mt-3' onClick={() => setReloadKey((current) => current + 1)}>
            Reintentar
          </Button>
        </div>
      ) : (
        <>
          {statistics ? (
            <LossAnalysis
              activeReasons={filters.reasons}
              measure={measure}
              onMeasure={setMeasure}
              onReason={(reason) =>
                apply({
                  ...filters,
                  reasons:
                    filters.reasons.length === 1 && filters.reasons[0] === reason ? [] : [reason],
                })
              }
              statistics={statistics}
            />
          ) : null}
          <section aria-labelledby='closed-history-title' className='closed-history'>
            <header className='closed-section-header'>
              <h2 id='closed-history-title'>Historial de pérdidas</h2>
              <div className='closed-history__tools'>
                {statistics ? (
                  <span>
                    {statistics.current_count}{' '}
                    {statistics.current_count === 1 ? 'oportunidad' : 'oportunidades'}
                  </span>
                ) : null}
                <SegmentedControl
                  label='Vista del historial'
                  onChange={(value) => {
                    const view = value === 'cards' ? 'cards' : 'table'
                    setResultView(view)
                    setResultViewQuery(new URLSearchParams(window.location.search), view)
                  }}
                  segments={LOST_RESULT_VIEWS}
                  value={resultView}
                />
              </div>
            </header>
            {items.length ? (
              resultView === 'cards' ? (
                <LostCards items={items} onOpen={setOpenOpportunityId} />
              ) : (
                <LostRows items={items} onOpen={setOpenOpportunityId} />
              )
            ) : (
              <div className='closed-history__empty'>
                <EmptyState
                  description={
                    filtered
                      ? 'Probá otro período o ajustá los filtros.'
                      : 'Las oportunidades cerradas como perdidas aparecerán aquí.'
                  }
                  icon='x-circle'
                  size='small'
                  title={
                    filtered ? 'No hay pérdidas con estos filtros' : 'No hay oportunidades perdidas'
                  }
                />
              </div>
            )}
            {pageError ? <InlineFeedback message={pageError} /> : null}
            {nextCursor ? (
              <footer className='won-pagination'>
                <span>
                  {items.length} de {statistics?.current_count ?? items.length} oportunidades
                </span>
                <Button
                  isLoading={loadingMore}
                  onClick={() => void loadMore()}
                  size='compact'
                  variant='secondary'
                >
                  Cargar más <Icon name='chevron-right' />
                </Button>
              </footer>
            ) : null}
          </section>
        </>
      )}
      {activeOpportunityId ? (
        <OpportunityDetailPage
          onClose={openOpportunityId ? () => setOpenOpportunityId(null) : undefined}
          onOpportunityDeleted={(id) => {
            setItems((current) => current.filter((item) => item.opportunity.id !== id))
            setReloadKey((current) => current + 1)
          }}
          opportunityId={activeOpportunityId}
          surface='lost'
        />
      ) : null}
    </section>
  )
}
