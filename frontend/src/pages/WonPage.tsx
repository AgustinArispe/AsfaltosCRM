import { useEffect, useMemo, useState } from 'react'
import type { ApiSession } from '../api/opportunities'
import { getWonFilterOptions, getWonStatistics, listWonOpportunities } from '../api/won'
import { useAuth } from '../auth/AuthContext'
import { SOURCE_LABELS } from '../pipeline/config'
import { isLeadSource } from '../pipeline/types'
import { navigateRoute } from '../routing/router'
import { Button } from '../shared/Button'
import { Input, Select } from '../shared/FormControls'
import { formatDateTime, formatDecimalKg } from '../shared/formatters'
import { Icon } from '../shared/Icon'
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
  const source = query.get('source')
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
    source: isLeadSource(source) ? source : '',
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
  const resetFilters = () => {
    setDraft(DEFAULT_FILTERS)
    setFilters(DEFAULT_FILTERS)
    window.history.replaceState(null, '', '/won')
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
    <section aria-label='Ganadas' className='won-workspace mx-auto w-full min-w-0 max-w-[90rem]'>
      <form
        aria-label='Filtrar Ganadas'
        className='won-filters'
        onSubmit={(event) => {
          event.preventDefault()
          apply()
        }}
      >
        <div className='won-filter won-filter--search'>
          <Icon className='won-filter__search-icon' name='search' />
          <Input
            className='won-filter__search-input'
            id='won-search'
            label='Buscar cliente, empresa o ID'
            value={draft.search}
            onChange={(event) => setDraft({ ...draft, search: event.target.value })}
          />
        </div>
        <div className='won-filter'>
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
        </div>
        {draft.period === 'custom' ? (
          <>
            <div className='won-filter'>
              <Input
                id='won-from'
                label='Desde'
                type='date'
                value={draft.from}
                onChange={(event) => setDraft({ ...draft, from: event.target.value })}
              />
            </div>
            <div className='won-filter'>
              <Input
                id='won-to'
                label='Hasta'
                type='date'
                value={draft.to}
                onChange={(event) => setDraft({ ...draft, to: event.target.value })}
              />
            </div>
          </>
        ) : null}
        <div className='won-filter'>
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
        </div>
        <div className='won-filter'>
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
        </div>
        <div className='won-filter'>
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
        </div>
        <div className='won-filter'>
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
        </div>
        <div className='won-filter-actions'>
          <Button size='compact' type='submit'>
            <Icon name='filter' />
            Aplicar
          </Button>
          <Button size='compact' type='button' variant='ghost' onClick={resetFilters}>
            Restablecer
          </Button>
        </div>
      </form>
      {statistics ? (
        <section aria-label='Resumen de Ganadas' className='won-summary'>
          <div className='won-summary-card'>
            <span className='won-summary-card__icon'>
              <Icon name='trophy' />
            </span>
            <span>
              <small>Ganadas</small>
              <strong>
                {statistics.won_count}{' '}
                {statistics.won_count === 1 ? 'oportunidad' : 'oportunidades'}
              </strong>
            </span>
          </div>
          <div className='won-summary-card'>
            <span className='won-summary-card__icon'>
              <Icon name='coins' />
            </span>
            <span>
              <small>Kg ganados</small>
              <strong>{formatDecimalKg(statistics.won_quantity_kg)}</strong>
            </span>
          </div>
        </section>
      ) : null}
      {error ? <InlineFeedback message={error} onDismiss={() => setError(null)} /> : null}
      {loading && items.length === 0 ? (
        <WorkspaceSkeleton label='Cargando Ganadas' />
      ) : items.length === 0 ? (
        <section className='won-empty-card ui-surface'>
          <EmptyState
            title='No hay oportunidades ganadas en este período'
            description='Probá otro período o ajustá los filtros.'
            icon='trophy'
            size='small'
            action={<Button onClick={resetFilters}>Restablecer filtros</Button>}
          />
        </section>
      ) : (
        <section aria-label='Historial de Ganadas' className='won-results'>
          <ul className='won-results__list'>
            {items.map((item) => (
              <li key={item.opportunity.id}>
                <button
                  aria-label={`Abrir oportunidad ${item.opportunity.id} de ${item.opportunity.customer.name}`}
                  className='won-result-card'
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
                  type='button'
                >
                  <span className='won-result-card__icon'>
                    <Icon name='trophy' />
                  </span>
                  <span className='won-result-card__customer'>
                    <strong>{item.opportunity.customer.name}</strong>
                    {item.opportunity.customer.company ? (
                      <span>{item.opportunity.customer.company}</span>
                    ) : null}
                  </span>
                  <span className='won-result-card__product'>
                    <small>Productos</small>
                    <span>{products(item)}</span>
                  </span>
                  <span className='won-result-card__quantity'>
                    <strong>{formatDecimalKg(item.won_total_kg)}</strong>
                    <small>Kg ganados</small>
                  </span>
                  <span className='won-result-card__meta'>
                    <span>{SOURCE_LABELS[item.opportunity.source]}</span>
                    <span>{item.opportunity.customer.province ?? 'Sin provincia'}</span>
                    <span>{item.opportunity.assigned_user?.full_name ?? 'Sin responsable'}</span>
                    <time dateTime={item.won_at}>{formatDateTime(item.won_at)}</time>
                  </span>
                  <Icon className='won-result-card__chevron' name='chevron-right' />
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
      {error && items.length === 0 ? (
        <Button onClick={() => setRetry((value) => value + 1)}>Reintentar</Button>
      ) : null}
      {nextCursor ? (
        <footer className='won-pagination'>
          <span>Más resultados disponibles</span>
          <Button
            isLoading={loadingMore}
            onClick={() => void loadMore()}
            size='compact'
            variant='secondary'
          >
            Cargar más
            <Icon name='chevron-right' />
          </Button>
        </footer>
      ) : null}
      {selectedOpportunityId ? (
        <OpportunityDetailPage opportunityId={selectedOpportunityId} surface='won' />
      ) : null}
    </section>
  )
}
