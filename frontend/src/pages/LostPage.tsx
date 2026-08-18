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
import { InlineFeedback } from '../shared/InlineFeedback'
import { EmptyState } from '../shared/StatusStates'
import { SearchField } from '../shared/Workspace'
import { WorkspaceSkeleton } from '../shared/WorkspaceSkeleton'

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
  return `${names.join(', ')}${item.loss_products.length > 2 ? ` +${item.loss_products.length - 2}` : ''} · ${formatDecimalKg(item.quoted_total_kg)}`
}

function LostRows({ items }: { items: LostOpportunity[] }) {
  return (
    <section aria-label='Oportunidades perdidas actuales' className='ui-panel overflow-x-auto'>
      <table className='w-full min-w-[48rem] border-collapse text-left text-sm'>
        <caption className='sr-only'>
          Oportunidades perdidas actuales, ordenadas por pérdida más reciente
        </caption>
        <thead>
          <tr className='border-b border-[var(--border-default)] bg-[var(--surface-subtle)] text-xs text-[var(--text-secondary)]'>
            <th className='px-4 py-3 font-semibold' scope='col'>
              Cliente
            </th>
            <th className='px-4 py-3 font-semibold' scope='col'>
              Motivo
            </th>
            <th className='px-4 py-3 font-semibold' scope='col'>
              Fecha de pérdida
            </th>
            <th className='hidden px-4 py-3 font-semibold lg:table-cell' scope='col'>
              Origen
            </th>
            <th className='hidden px-4 py-3 font-semibold xl:table-cell' scope='col'>
              Cotización
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
                className='border-b border-[var(--border-subtle)] last:border-b-0 hover:bg-[var(--hover)]'
                key={item.loss_event_id}
              >
                <th className='px-4 py-3 font-semibold text-[var(--text-primary)]' scope='row'>
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
                      {opportunity.is_reopened ? (
                        <span className='mt-1 block text-xs font-normal text-[var(--text-secondary)]'>
                          Reabierta previamente
                        </span>
                      ) : null}
                    </span>
                  </AppLink>
                </th>
                <td className='px-4 py-3'>
                  <Badge tone='lost'>{LOSS_REASON_LABELS[item.loss_reason]}</Badge>
                </td>
                <td className='whitespace-nowrap px-4 py-3 text-[var(--text-secondary)]'>
                  <time dateTime={item.lost_at}>{formatDateTime(item.lost_at)}</time>
                </td>
                <td className='hidden px-4 py-3 text-[var(--text-secondary)] lg:table-cell'>
                  {SOURCE_LABELS[opportunity.source]}
                </td>
                <td className='hidden max-w-xs px-4 py-3 text-xs text-[var(--text-secondary)] xl:table-cell'>
                  {productEvidence(item)}
                </td>
                <td className='px-4 py-3 text-right'>
                  <AppLink
                    className='inline-flex min-h-11 items-center px-2 text-sm font-semibold outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]'
                    origin={{ kind: 'workspace', workspace: 'lost' }}
                    to={{ kind: 'opportunity', opportunityId: opportunity.id, surface: 'lost' }}
                  >
                    Abrir
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
  return (
    <section aria-label='Resumen de pérdidas' className='lost-statistics'>
      <div>
        <p>Perdidas actuales</p>
        <p className='mt-1 text-lg font-semibold tabular-nums'>
          {statistics.current_count}{' '}
          <span className='text-sm font-medium'>
            {formatDecimalKg(statistics.current_quantity_kg)}
          </span>
        </p>
      </div>
      <div>
        <p>Episodios históricos</p>
        <p className='mt-1 text-lg font-semibold tabular-nums'>
          {statistics.historical_loss_count}{' '}
          <span className='text-sm font-medium'>
            {formatDecimalKg(statistics.historical_quantity_kg)}
          </span>
        </p>
      </div>
      <div>
        <p>Episodios reabiertos</p>
        <p className='mt-1 text-lg font-semibold tabular-nums'>{statistics.reopened_count}</p>
      </div>
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
    <section aria-label='Oportunidades perdidas' className='mx-auto max-w-[90rem]'>
      <div className='flex flex-wrap justify-end gap-4'>
        {filterCount ? (
          <p className='text-sm text-[var(--text-secondary)]'>
            {filterCount} {filterCount === 1 ? 'filtro activo' : 'filtros activos'}
          </p>
        ) : null}
      </div>
      <form
        className='ui-toolbar ui-toolbar--divided mt-4'
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
        <fieldset className='flex flex-wrap gap-1'>
          <legend className='mb-1 text-xs font-semibold text-[var(--text-secondary)]'>
            Motivo
          </legend>
          {LOSS_REASON_OPTIONS.map((option) => (
            <label
              className='inline-flex min-h-9 items-center gap-1.5 rounded-[var(--radius-control)] border border-[var(--border-default)] px-2 text-xs'
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
        </fieldset>
        <details className='relative'>
          <summary className='ui-pressable min-h-11 cursor-pointer rounded-[var(--radius-control)] border border-[var(--border-default)] px-3 py-2 text-sm font-semibold'>
            Filtros{filterCount ? ` · ${filterCount}` : ''}
          </summary>
          <div className='absolute right-0 z-20 mt-2 grid w-72 gap-3 rounded-[var(--radius-surface)] border border-[var(--border-default)] bg-[var(--surface-overlay)] p-3 shadow-[var(--shadow-raised)]'>
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
        <Button type='submit' variant='primary'>
          Aplicar
        </Button>
        {filterCount ? (
          <Button onClick={reset} type='button'>
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
