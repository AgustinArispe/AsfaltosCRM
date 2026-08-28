import { useEffect, useMemo, useState } from 'react'
import { listCustomers } from '../api/customers'
import { getLostStatistics, listLostOpportunities } from '../api/lost'
import type { ApiSession } from '../api/opportunities'
import { listProducts } from '../api/products'
import { useAuth } from '../auth/AuthContext'
import {
  EMPTY_LOST_FILTERS,
  type LostFilters,
  type LostOpportunity,
  type LostStatistics,
} from '../lost/types'
import { LOSS_REASON_LABELS, LOSS_REASON_OPTIONS, SOURCE_LABELS } from '../pipeline/config'
import type { LossReason } from '../pipeline/types'
import { AppLink } from '../routing/router'
import { Badge } from '../shared/Badge'
import { Button } from '../shared/Button'
import { formatDateTime, formatDecimalKg } from '../shared/formatters'
import { EmptyState, InlineFeedback, WorkspaceSkeleton } from '../shared/StatusStates'
import { SearchField } from '../shared/Workspace'

function activeFilterCount(filters: LostFilters): number {
  return (
    Number(Boolean(filters.search)) +
    filters.reasons.length +
    Number(Boolean(filters.customerId)) +
    Number(Boolean(filters.province)) +
    Number(Boolean(filters.productId)) +
    Number(Boolean(filters.source)) +
    Number(Boolean(filters.lostFrom)) +
    Number(Boolean(filters.lostTo))
  )
}

function productEvidence(item: LostOpportunity): string {
  if (item.loss_products.length === 0) return 'Sin cotización'
  const names = item.loss_products.slice(0, 2).map((product) => product.product_name)
  return `${names.join(', ')}${item.loss_products.length > 2 ? ` +${item.loss_products.length - 2}` : ''}`
}

function lossReasonLabel(key: string): string {
  return (
    LOSS_REASON_LABELS[key as LossReason] ?? key.toLocaleLowerCase('es-AR').replaceAll('_', ' ')
  )
}

function LostRows({ items }: { items: LostOpportunity[] }) {
  return (
    <section aria-label='Oportunidades perdidas actuales' className='lost-list overflow-x-auto'>
      <table className='w-full min-w-[50rem] border-collapse text-left text-sm'>
        <caption className='sr-only'>
          Oportunidades perdidas actuales, ordenadas por pérdida más reciente
        </caption>
        <thead>
          <tr className='lost-list__heading border-b border-[var(--border-default)] text-xs text-[var(--text-secondary)]'>
            <th className='px-4 py-3 font-semibold' scope='col'>
              Cliente
            </th>
            <th className='px-4 py-3 font-semibold' scope='col'>
              Evidencia comercial
            </th>
            <th className='px-4 py-3 font-semibold' scope='col'>
              Motivo de pérdida
            </th>
            <th className='px-4 py-3 font-semibold' scope='col'>
              Fecha de pérdida
            </th>
            <th className='px-4 py-3 text-right font-semibold' scope='col'>
              <span className='sr-only'>Abrir</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const opportunity = item.opportunity
            return (
              <tr
                className='lost-list__row border-b border-[var(--border-subtle)] last:border-b-0 hover:bg-[var(--hover)]'
                key={item.loss_event_id}
              >
                <th
                  className='lost-list__customer px-4 py-3 font-semibold text-[var(--text-primary)]'
                  scope='row'
                >
                  <AppLink
                    aria-label={opportunity.customer.name}
                    className='inline-flex min-h-11 items-center outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]'
                    origin={{ kind: 'workspace', workspace: 'lost' }}
                    to={{ kind: 'opportunity', opportunityId: opportunity.id, surface: 'lost' }}
                  >
                    <span>
                      {opportunity.customer.name}
                      {opportunity.customer.company ? (
                        <span className='mt-0.5 block font-normal text-[var(--text-secondary)]'>
                          {opportunity.customer.company}
                        </span>
                      ) : null}
                      <span className='mt-1 block text-xs font-normal text-[var(--text-tertiary)]'>
                        {SOURCE_LABELS[opportunity.source]}
                      </span>
                      {opportunity.is_reopened ? (
                        <span className='mt-1 block text-xs font-normal text-[var(--text-secondary)]'>
                          Reabierta previamente
                        </span>
                      ) : null}
                    </span>
                  </AppLink>
                </th>
                <td className='lost-list__quote px-4 py-3'>
                  <strong className='block text-sm tabular-nums text-[var(--brand-deep)]'>
                    {formatDecimalKg(item.quoted_total_kg)}
                  </strong>
                  <span className='mt-0.5 block text-xs'>{productEvidence(item)}</span>
                </td>
                <td className='lost-list__reason px-4 py-3'>
                  <Badge tone='lost'>{LOSS_REASON_LABELS[item.loss_reason]}</Badge>
                </td>
                <td className='lost-list__date whitespace-nowrap px-4 py-3 text-[var(--text-secondary)]'>
                  <time dateTime={item.lost_at}>{formatDateTime(item.lost_at)}</time>
                </td>
                <td className='px-4 py-3 text-right'>
                  <AppLink
                    className='inline-flex min-h-11 items-center px-2 text-sm font-semibold outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]'
                    origin={{ kind: 'workspace', workspace: 'lost' }}
                    to={{ kind: 'opportunity', opportunityId: opportunity.id, surface: 'lost' }}
                  >
                    Abrir oportunidad
                  </AppLink>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </section>
  )
}

function Statistics({ statistics }: { statistics: LostStatistics }) {
  const maxReasonCount = Math.max(1, ...statistics.by_reason.map((reason) => reason.count))
  return (
    <section aria-label='Análisis de pérdidas' className='lost-analysis'>
      <section aria-label='Resumen de pérdidas' className='lost-statistics'>
        <div className='lost-statistics__primary'>
          <p>Pérdidas actuales</p>
          <strong>{statistics.current_count}</strong>
          <span>{formatDecimalKg(statistics.current_quantity_kg)} perdidos</span>
        </div>
        <div>
          <p>Histórico</p>
          <strong>{statistics.historical_loss_count}</strong>
          <span>{formatDecimalKg(statistics.historical_quantity_kg)}</span>
        </div>
        <div>
          <p>Reabiertas</p>
          <strong>{statistics.reopened_count}</strong>
        </div>
      </section>
      <section aria-labelledby='lost-reasons-title' className='lost-reasons'>
        <h2 id='lost-reasons-title'>Motivos de pérdida</h2>
        {statistics.by_reason.length ? (
          <ul>
            {statistics.by_reason.map((reason) => (
              <li key={reason.key}>
                <span>{lossReasonLabel(reason.key)}</span>
                <strong className='lost-reasons__count'>{reason.count}</strong>
                <span className='lost-reasons__track' aria-hidden='true'>
                  <span style={{ width: `${(reason.count / maxReasonCount) * 100}%` }} />
                </span>
                <small className='lost-reasons__quantity'>
                  {formatDecimalKg(reason.quantity_kg)}
                </small>
              </li>
            ))}
          </ul>
        ) : (
          <p className='lost-reasons__empty'>Sin motivos para este período.</p>
        )}
      </section>
    </section>
  )
}

export function LostPage() {
  const { token, logout, user } = useAuth()
  const session = useMemo<ApiSession>(
    () => ({ token: token ?? '', onUnauthorized: logout }),
    [logout, token],
  )
  const [draft, setDraft] = useState<LostFilters>(EMPTY_LOST_FILTERS)
  const [filters, setFilters] = useState<LostFilters>(EMPTY_LOST_FILTERS)
  const [items, setItems] = useState<LostOpportunity[]>([])
  const [nextCursor, setNextCursor] = useState<string | null>(null)
  const [statistics, setStatistics] = useState<LostStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [customers, setCustomers] = useState<
    Array<{ id: number; name: string; company: string | null }>
  >([])
  const [products, setProducts] = useState<Array<{ id: number; name: string }>>([])
  const filterCount = activeFilterCount(filters)

  useEffect(() => {
    void reloadKey
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    Promise.all([
      listLostOpportunities(filters, null, { ...session, signal: controller.signal }),
      getLostStatistics(filters, { ...session, signal: controller.signal }),
    ])
      .then(([page, summary]) => {
        setItems(page.items)
        setNextCursor(page.next_cursor)
        setStatistics(summary)
      })
      .catch((caught: unknown) => {
        if (!(caught instanceof DOMException && caught.name === 'AbortError'))
          setError(
            'No pudimos cargar las oportunidades perdidas. Revisá tu conexión e intentá nuevamente.',
          )
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [filters, reloadKey, session])

  useEffect(() => {
    if (!user) return
    Promise.all([
      listCustomers({ page: 1, pageSize: 100 }, session),
      listProducts(user.role === 'SUPERVISOR', session),
    ])
      .then(([customerPage, catalog]) => {
        setCustomers(customerPage.items)
        setProducts(catalog.map((product) => ({ id: product.id, name: product.name })))
      })
      .catch(() => undefined)
  }, [session, user])

  if (!user) return null
  const updateDraft = <K extends keyof LostFilters>(key: K, value: LostFilters[K]) =>
    setDraft((current) => ({ ...current, [key]: value }))
  const applyFilters = () =>
    setFilters({ ...draft, search: draft.search.trim(), province: draft.province.trim() })
  const reset = () => {
    setDraft(EMPTY_LOST_FILTERS)
    setFilters(EMPTY_LOST_FILTERS)
  }
  const toggleReason = (reason: LossReason) =>
    setDraft((current) => ({
      ...current,
      reasons: current.reasons.includes(reason)
        ? current.reasons.filter((value) => value !== reason)
        : [...current.reasons, reason],
    }))
  const loadMore = async () => {
    if (!nextCursor || loadingMore) return
    setLoadingMore(true)
    try {
      const page = await listLostOpportunities(filters, nextCursor, session)
      setItems((current) => [...current, ...page.items])
      setNextCursor(page.next_cursor)
    } catch {
      setError('No pudimos cargar más oportunidades perdidas. Intentá nuevamente.')
    } finally {
      setLoadingMore(false)
    }
  }

  return (
    <section aria-label='Oportunidades perdidas' className='lost-workspace mx-auto max-w-[90rem]'>
      <form
        aria-label='Filtrar pérdidas'
        className='ui-toolbar ui-toolbar--divided'
        onSubmit={(event) => {
          event.preventDefault()
          applyFilters()
        }}
      >
        <SearchField
          label='Buscar'
          className='max-w-sm'
          onChange={(event) => updateDraft('search', event.target.value)}
          placeholder='Cliente o empresa'
          type='search'
          value={draft.search}
        />
        <details className='lost-filters relative'>
          <summary className='ui-pressable min-h-9 cursor-pointer rounded-[var(--radius-control)] border border-[var(--border-default)] px-3 py-1.5 text-xs font-semibold'>
            Filtros{filterCount ? ` · ${filterCount}` : ''}
          </summary>
          <div className='lost-filters__panel absolute right-0 z-20 mt-2 grid w-80 gap-3 rounded-[var(--radius-surface)] border border-[var(--border-default)] bg-[var(--surface-overlay)] p-3 shadow-[var(--shadow-raised)]'>
            <fieldset className='grid gap-1.5'>
              <legend className='mb-1 text-xs font-semibold text-[var(--text-secondary)]'>
                Motivo
              </legend>
              <div className='flex flex-wrap gap-1'>
                {LOSS_REASON_OPTIONS.map((option) => (
                  <label
                    className={[
                      'lost-reason-filter inline-flex min-h-9 items-center gap-1.5 rounded-full border px-2.5 text-xs font-medium',
                      draft.reasons.includes(option.value) ? 'lost-reason-filter--selected' : '',
                    ].join(' ')}
                    key={option.value}
                  >
                    <input
                      checked={draft.reasons.includes(option.value)}
                      onChange={() => toggleReason(option.value)}
                      type='checkbox'
                    />
                    {option.label}
                  </label>
                ))}
              </div>
            </fieldset>
            <label className='ui-label'>
              Cliente
              <select
                className='ui-field'
                onChange={(event) =>
                  updateDraft('customerId', event.target.value ? Number(event.target.value) : null)
                }
                value={draft.customerId ?? ''}
              >
                <option value=''>Todos</option>
                {customers.map((customer) => (
                  <option key={customer.id} value={customer.id}>
                    {customer.name}
                    {customer.company ? ` · ${customer.company}` : ''}
                  </option>
                ))}
              </select>
            </label>
            <label className='ui-label'>
              Provincia
              <input
                className='ui-field'
                onChange={(event) => updateDraft('province', event.target.value)}
                value={draft.province}
              />
            </label>
            <label className='ui-label'>
              Producto
              <select
                className='ui-field'
                onChange={(event) =>
                  updateDraft('productId', event.target.value ? Number(event.target.value) : null)
                }
                value={draft.productId ?? ''}
              >
                <option value=''>Todos</option>
                {products.map((product) => (
                  <option key={product.id} value={product.id}>
                    {product.name}
                  </option>
                ))}
              </select>
            </label>
            <label className='ui-label'>
              Origen
              <select
                className='ui-field'
                onChange={(event) =>
                  updateDraft('source', event.target.value as LostFilters['source'])
                }
                value={draft.source}
              >
                <option value=''>Todos</option>
                <option value='WEB'>Web</option>
                <option value='WHATSAPP'>WhatsApp</option>
              </select>
            </label>
            <label className='ui-label'>
              Desde
              <input
                className='ui-field'
                onChange={(event) => updateDraft('lostFrom', event.target.value)}
                type='date'
                value={draft.lostFrom}
              />
            </label>
            <label className='ui-label'>
              Hasta (sin incluir)
              <input
                className='ui-field'
                onChange={(event) => updateDraft('lostTo', event.target.value)}
                type='date'
                value={draft.lostTo}
              />
            </label>
          </div>
        </details>
        <Button size='compact' type='submit'>
          Aplicar
        </Button>
        {filterCount ? (
          <Button onClick={reset} size='compact' type='button' variant='ghost'>
            Restablecer
          </Button>
        ) : null}
      </form>
      <div className='mt-4'>
        {loading ? (
          <WorkspaceSkeleton label='Cargando pérdidas…' />
        ) : error ? (
          <div className='ui-panel p-5'>
            <InlineFeedback message={error} />
            <Button className='mt-3' onClick={() => setReloadKey((current) => current + 1)}>
              Reintentar
            </Button>
          </div>
        ) : (
          <>
            {statistics ? <Statistics statistics={statistics} /> : null}
            <div className='mt-4'>
              {items.length ? (
                <LostRows items={items} />
              ) : (
                <EmptyState
                  description={
                    filterCount
                      ? 'Modificá o restablecé los filtros para ampliar la búsqueda.'
                      : 'Las oportunidades perdidas actuales aparecerán aquí.'
                  }
                  icon='alert'
                  size='workspace'
                  title={
                    filterCount
                      ? 'No hay pérdidas con estos filtros'
                      : 'No hay oportunidades perdidas'
                  }
                />
              )}
            </div>
            {nextCursor ? (
              <div className='mt-3 text-center'>
                <Button disabled={loadingMore} onClick={() => void loadMore()}>
                  {loadingMore ? 'Cargando…' : 'Cargar más'}
                </Button>
              </div>
            ) : null}
          </>
        )}
      </div>
    </section>
  )
}
