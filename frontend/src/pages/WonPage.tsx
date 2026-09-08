import { useEffect, useMemo, useState } from 'react'
import type { ApiSession } from '../api/opportunities'
import { getWonFilterOptions, getWonStatistics, listWonOpportunities } from '../api/won'
import { useAuth } from '../auth/AuthContext'
import { SOURCE_LABELS } from '../pipeline/config'
import { navigateRoute } from '../routing/router'
import { Button } from '../shared/Button'
import { Input, Select } from '../shared/FormControls'
import { formatDateTime, formatDecimalKg } from '../shared/formatters'
import { EmptyState, InlineFeedback, WorkspaceSkeleton } from '../shared/StatusStates'
import type { WonFilterOptions, WonFilters, WonOpportunity, WonStatistics } from '../won/types'
import { OpportunityDetailPage } from './OpportunityDetailPage'

function buenosAiresToday(): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Argentina/Buenos_Aires',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date())
}
function periodDates(period: WonFilters['period']): Pick<WonFilters, 'from' | 'to'> {
  if (period === 'all') return { from: '', to: '' }
  const today = buenosAiresToday()
  const [year, month] = today.split('-').map(Number)
  if (year === undefined || month === undefined) return { from: '', to: '' }
  const start =
    period === 'year'
      ? `${year}-01-01`
      : period === 'three-months'
        ? new Date(Date.UTC(year, month - 3, 1)).toISOString().slice(0, 10)
        : `${year}-${String(month).padStart(2, '0')}-01`
  return { from: start, to: today }
}
const DEFAULT_FILTERS: WonFilters = {
  period: 'month',
  ...periodDates('month'),
  search: '',
  product: '',
  source: '',
  province: '',
  responsible: '',
  unassigned: false,
}
function readFilters(): WonFilters {
  const query = new URLSearchParams(window.location.search)
  const period = query.get('period')
  const validPeriod =
    period === 'three-months' ||
    period === 'year' ||
    period === 'custom' ||
    period === 'all' ||
    period === 'month'
      ? period
      : 'month'
  return {
    ...DEFAULT_FILTERS,
    ...periodDates(validPeriod),
    period: validPeriod,
    from: query.get('from') ?? periodDates(validPeriod).from,
    to: query.get('to') ?? periodDates(validPeriod).to,
    search: query.get('search') ?? '',
    source: (query.get('source') as WonFilters['source']) ?? '',
    product: query.get('product') ?? '',
    province: query.get('province') ?? '',
    responsible: query.get('responsible') ?? '',
    unassigned: query.get('unassigned') === 'true',
  }
}
function products(item: WonOpportunity): string {
  return item.opportunity.products
    .map((line) => `${line.product.name} (${formatDecimalKg(line.quantity_kg)})`)
    .join(', ')
}

export function WonPage({ selectedOpportunityId }: { selectedOpportunityId?: number }) {
  const { token, logout } = useAuth()
  const session = useMemo<ApiSession>(
    () => ({ token: token ?? '', onUnauthorized: logout }),
    [logout, token],
  )
  const [draft, setDraft] = useState<WonFilters>(readFilters)
  const [filters, setFilters] = useState<WonFilters>(readFilters)
  const [items, setItems] = useState<WonOpportunity[]>([])
  const [statistics, setStatistics] = useState<WonStatistics | null>(null)
  const [options, setOptions] = useState<WonFilterOptions | null>(null)
  const [nextCursor, setNextCursor] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    getWonFilterOptions(session)
      .then(setOptions)
      .catch(() => undefined)
  }, [session])
  useEffect(() => {
    void retry
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    Promise.allSettled([
      listWonOpportunities(filters, null, { ...session, signal: controller.signal }),
      getWonStatistics(filters, { ...session, signal: controller.signal }),
    ])
      .then(([page, stats]) => {
        if (controller.signal.aborted) return
        if (page.status === 'fulfilled') {
          setItems(page.value.items)
          setNextCursor(page.value.next_cursor)
        } else setError('No pudimos cargar la lista de Ganadas.')
        if (stats.status === 'fulfilled') setStatistics(stats.value)
        else setError((current) => current ?? 'No pudimos cargar el resumen de Ganadas.')
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [filters, retry, session])
  const apply = () => {
    const next = { ...draft, search: draft.search.trim(), province: draft.province.trim() }
    const query = new URLSearchParams()
    ;(
      ['period', 'from', 'to', 'search', 'source', 'product', 'province', 'responsible'] as const
    ).forEach((key) => {
      if (next[key]) query.set(key, next[key])
    })
    if (next.unassigned) query.set('unassigned', 'true')
    window.history.replaceState(window.history.state, '', `/won?${query}`)
    setFilters(next)
  }
  const changePeriod = (period: WonFilters['period']) =>
    setDraft((current) => ({ ...current, period, ...periodDates(period) }))
  const loadMore = async () => {
    if (!nextCursor) return
    setLoadingMore(true)
    try {
      const page = await listWonOpportunities(filters, nextCursor, session)
      setItems((current) => [...current, ...page.items])
      setNextCursor(page.next_cursor)
    } catch {
      setError('No pudimos cargar más resultados.')
    } finally {
      setLoadingMore(false)
    }
  }
  return (
    <section aria-label='Ganadas' className='mx-auto w-full min-w-0 max-w-[90rem] space-y-4'>
      <form
        aria-label='Filtrar Ganadas'
        className='ui-toolbar grid gap-3 md:grid-cols-4'
        onSubmit={(event) => {
          event.preventDefault()
          apply()
        }}
      >
        <Input
          id='won-search'
          label='Buscar cliente, empresa o ID'
          value={draft.search}
          onChange={(event) => setDraft({ ...draft, search: event.target.value })}
        />
        <Select
          id='won-period'
          label='Período'
          value={draft.period}
          onChange={(event) => changePeriod(event.target.value as WonFilters['period'])}
        >
          <option value='month'>Este mes</option>
          <option value='three-months'>Últimos 3 meses</option>
          <option value='year'>Este año</option>
          <option value='custom'>Personalizado</option>
          <option value='all'>Todo el historial</option>
        </Select>
        {draft.period === 'custom' ? (
          <>
            <Input
              id='won-from'
              label='Desde'
              type='date'
              value={draft.from}
              onChange={(event) => setDraft({ ...draft, from: event.target.value })}
            />
            <Input
              id='won-to'
              label='Hasta'
              type='date'
              value={draft.to}
              onChange={(event) => setDraft({ ...draft, to: event.target.value })}
            />
          </>
        ) : null}
        <Select
          id='won-product'
          label='Producto'
          value={draft.product}
          onChange={(event) => setDraft({ ...draft, product: event.target.value })}
        >
          <option value=''>Todos</option>
          {options?.products.map((option) => (
            <option key={option.id} value={option.id}>
              {option.name}
              {option.is_active ? '' : ' (inactivo)'}
            </option>
          ))}
        </Select>
        <Select
          id='won-source'
          label='Origen'
          value={draft.source}
          onChange={(event) =>
            setDraft({ ...draft, source: event.target.value as WonFilters['source'] })
          }
        >
          <option value=''>Todos</option>
          {Object.entries(SOURCE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
        <Select
          id='won-province'
          label='Provincia'
          value={draft.province}
          onChange={(event) => setDraft({ ...draft, province: event.target.value })}
        >
          <option value=''>Todas</option>
          {options?.provinces.map((value) => (
            <option key={value}>{value}</option>
          ))}
        </Select>
        <Select
          id='won-responsible'
          label='Responsable'
          value={draft.unassigned ? 'unassigned' : draft.responsible}
          onChange={(event) =>
            setDraft({
              ...draft,
              responsible: event.target.value === 'unassigned' ? '' : event.target.value,
              unassigned: event.target.value === 'unassigned',
            })
          }
        >
          <option value=''>Todos</option>
          <option value='unassigned'>Sin responsable</option>
          {options?.responsible_users.map((option) => (
            <option key={option.id} value={option.id}>
              {option.full_name}
              {option.is_active ? '' : ' (inactivo)'}
            </option>
          ))}
        </Select>
        <div className='flex items-end gap-2'>
          <Button type='submit'>Aplicar</Button>
          <Button
            type='button'
            variant='ghost'
            onClick={() => {
              setDraft(DEFAULT_FILTERS)
              setFilters(DEFAULT_FILTERS)
              window.history.replaceState(null, '', '/won')
            }}
          >
            Restablecer
          </Button>
        </div>
      </form>
      {statistics ? (
        <section aria-label='Resumen de Ganadas' className='grid grid-cols-2 gap-3'>
          <div className='ui-surface p-4'>
            <p>Total Ganadas</p>
            <strong className='text-2xl tabular-nums'>{statistics.won_count}</strong>
          </div>
          <div className='ui-surface p-4'>
            <p>Total kg ganados</p>
            <strong className='text-2xl tabular-nums'>
              {formatDecimalKg(statistics.won_quantity_kg)}
            </strong>
          </div>
        </section>
      ) : null}
      {error ? <InlineFeedback message={error} onDismiss={() => setError(null)} /> : null}
      {loading && items.length === 0 ? (
        <WorkspaceSkeleton label='Cargando Ganadas' />
      ) : items.length === 0 ? (
        <EmptyState
          title={filters.period === 'month' ? 'Todavía no hay Ganadas este mes' : 'Sin resultados'}
          description='Probá otro período o restablecé los filtros.'
          icon='search'
          action={
            <Button
              onClick={() => {
                setDraft(DEFAULT_FILTERS)
                setFilters(DEFAULT_FILTERS)
              }}
            >
              Restablecer
            </Button>
          }
        />
      ) : (
        <section aria-label='Historial de Ganadas'>
          <div className='grid gap-3 md:hidden'>
            {items.map((item) => (
              <article className='ui-surface grid gap-3 p-4 text-sm' key={item.opportunity.id}>
                <div>
                  <p className='text-xs text-[var(--text-muted)]'>Fecha de ganancia</p>
                  <time dateTime={item.won_at}>{formatDateTime(item.won_at)}</time>
                </div>
                <div>
                  <p className='text-xs text-[var(--text-muted)]'>Cliente / empresa</p>
                  <strong>{item.opportunity.customer.name}</strong>
                  {item.opportunity.customer.company ? (
                    <span className='block'>{item.opportunity.customer.company}</span>
                  ) : null}
                </div>
                <div>
                  <p className='text-xs text-[var(--text-muted)]'>Productos y cantidades</p>
                  <p>{products(item)}</p>
                </div>
                <dl className='grid grid-cols-2 gap-3'>
                  <div>
                    <dt className='text-xs text-[var(--text-muted)]'>Kg ganados</dt>
                    <dd>{formatDecimalKg(item.won_total_kg)}</dd>
                  </div>
                  <div>
                    <dt className='text-xs text-[var(--text-muted)]'>Origen</dt>
                    <dd>{SOURCE_LABELS[item.opportunity.source]}</dd>
                  </div>
                  <div>
                    <dt className='text-xs text-[var(--text-muted)]'>Provincia</dt>
                    <dd>{item.opportunity.customer.province ?? '—'}</dd>
                  </div>
                  <div>
                    <dt className='text-xs text-[var(--text-muted)]'>Responsable</dt>
                    <dd>{item.opportunity.assigned_user?.full_name ?? 'Sin responsable'}</dd>
                  </div>
                </dl>
                <Button
                  variant='ghost'
                  onClick={() =>
                    navigateRoute(
                      {
                        kind: 'opportunity',
                        opportunityId: item.opportunity.id,
                        surface: 'won',
                      },
                      {
                        origin: { kind: 'workspace', workspace: 'won' },
                        search: window.location.search,
                      },
                    )
                  }
                >
                  Abrir oportunidad
                </Button>
              </article>
            ))}
          </div>
          <div className='hidden w-full min-w-0 overflow-x-auto md:block'>
            <table className='w-full min-w-[58rem] text-left text-sm'>
              <thead>
                <tr>
                  <th>Fecha de ganancia</th>
                  <th>Cliente / empresa</th>
                  <th>Productos y cantidades</th>
                  <th>Kg ganados</th>
                  <th>Origen</th>
                  <th>Provincia</th>
                  <th>Responsable</th>
                  <th>
                    <span className='sr-only'>Acción</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.opportunity.id} className='border-t border-[var(--border-subtle)]'>
                    <td>
                      <time dateTime={item.won_at}>{formatDateTime(item.won_at)}</time>
                    </td>
                    <th scope='row'>
                      {item.opportunity.customer.name}
                      <span className='block font-normal'>{item.opportunity.customer.company}</span>
                    </th>
                    <td>{products(item)}</td>
                    <td>{formatDecimalKg(item.won_total_kg)}</td>
                    <td>{SOURCE_LABELS[item.opportunity.source]}</td>
                    <td>{item.opportunity.customer.province ?? '—'}</td>
                    <td>{item.opportunity.assigned_user?.full_name ?? 'Sin responsable'}</td>
                    <td>
                      <Button
                        variant='ghost'
                        onClick={() =>
                          navigateRoute(
                            {
                              kind: 'opportunity',
                              opportunityId: item.opportunity.id,
                              surface: 'won',
                            },
                            {
                              origin: { kind: 'workspace', workspace: 'won' },
                              search: window.location.search,
                            },
                          )
                        }
                      >
                        Abrir oportunidad
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
      {error && items.length === 0 ? (
        <Button onClick={() => setRetry((value) => value + 1)}>Reintentar</Button>
      ) : null}
      {nextCursor ? (
        <Button disabled={loadingMore} onClick={() => void loadMore()}>
          {loadingMore ? 'Cargando…' : 'Cargar más'}
        </Button>
      ) : null}
      {selectedOpportunityId ? (
        <OpportunityDetailPage opportunityId={selectedOpportunityId} surface='won' />
      ) : null}
    </section>
  )
}
