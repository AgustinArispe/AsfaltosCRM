import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { LostStatistics } from '../lost/types'
import { LostPage } from './LostPage'

const auth = vi.hoisted(() => ({
  logout: vi.fn(),
  user: {
    id: 1,
    full_name: 'FAA',
    email: 'faa@test',
    role: 'SUPERVISOR' as const,
    is_active: true,
  },
}))
vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({ token: 'lost-token', logout: auth.logout, user: auth.user }),
}))

vi.mock('./OpportunityDetailPage', () => ({
  OpportunityDetailPage: ({
    onOpportunityDeleted,
    opportunityId,
  }: {
    onOpportunityDeleted?: (opportunityId: number) => void
    opportunityId: number
  }) => (
    <button onClick={() => onOpportunityDeleted?.(opportunityId)} type='button'>
      Simular eliminación perdida
    </button>
  ),
}))

function response(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}
const lostItem = {
  loss_event_id: 99,
  loss_reason: 'PRECIO',
  from_status: 'COTIZADA',
  customer_province: 'Buenos Aires',
  lost_at: '2026-08-14T12:00:00Z',
  quoted_total_kg: '1250.500',
  loss_products: [{ product_id: 1, product_name: 'Asfalto', quantity_kg: '1250.500' }],
  opportunity: {
    id: 8,
    status: 'PERDIDA',
    source: 'WEB',
    current_status_entered_at: '2026-08-14T12:00:00Z',
    customer: {
      id: 4,
      name: 'Constructora Sur',
      company: 'Sur SA',
      email: null,
      phone: null,
      province: 'Buenos Aires',
      legendary_historical_override: false,
    },
    assigned_user: null,
    products: [],
    created_at: '2026-08-01T12:00:00Z',
    is_reopened: true,
    reopen_count: 1,
  },
}

describe('LostPage', () => {
  let statistics: LostStatistics

  it('applies shared 15-day dates to losses and removes bounds for Todo', async () => {
    render(<LostPage />)
    await screen.findByText('Constructora Sur')
    const count = (fetch as ReturnType<typeof vi.fn>).mock.calls.length
    fireEvent.click(screen.getByRole('button', { name: 'Últimos 15 días' }))
    expect(fetch).toHaveBeenCalledTimes(count)
    expect(screen.queryByLabelText('Desde')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Aplicar' }))
    await waitFor(() => expect(window.location.search).toContain('period=last-15-days'))
    const { from, to } = Object.fromEntries(new URLSearchParams(window.location.search))
    expect((Date.parse(to) - Date.parse(from)) / 86400000).toBe(14)
    expect(
      (fetch as ReturnType<typeof vi.fn>).mock.calls
        .slice(count)
        .every(
          ([url]) =>
            new URL(String(url), 'http://localhost').searchParams.get('lost_from') ===
            `${from}T00:00:00-03:00`,
        ),
    ).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: 'Todo' }))
    fireEvent.click(screen.getByRole('button', { name: 'Aplicar' }))
    await waitFor(() => expect(window.location.search).toBe('?period=all'))
    const last = (fetch as ReturnType<typeof vi.fn>).mock.calls.at(-1)
    expect(String(last?.[0])).not.toContain('lost_from')
    expect(String(last?.[0])).not.toContain('lost_to')
  })

  it('reveals custom dates on demand and applies the edited range', async () => {
    render(<LostPage />)
    await screen.findByText('Constructora Sur')
    fireEvent.change(screen.getByLabelText('Más períodos'), { target: { value: 'custom' } })
    fireEvent.change(screen.getByLabelText('Desde'), { target: { value: '2026-08-01' } })
    fireEvent.change(screen.getByLabelText('Hasta'), { target: { value: '2026-08-31' } })
    fireEvent.click(screen.getByRole('button', { name: 'Aplicar' }))
    await waitFor(() => expect(window.location.search).toContain('period=custom'))
    expect(window.location.search).toContain('from=2026-08-01&to=2026-08-31')
  })

  it('restores the period after incomplete custom dates', async () => {
    render(<LostPage />)
    await screen.findByText('Constructora Sur')
    fireEvent.change(screen.getByLabelText('Más períodos'), { target: { value: 'custom' } })
    fireEvent.change(screen.getByLabelText('Desde'), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: 'Restablecer' }))
    expect(screen.queryByLabelText('Desde')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Este mes', pressed: true })).toBeInTheDocument()
  })

  beforeEach(() => {
    window.history.replaceState(null, '', '/lost')
    statistics = {
      current_count: 1,
      current_quantity_kg: '1250.500',
      historical_loss_count: 3,
      historical_quantity_kg: '2500.500',
      reopened_count: 1,
      without_quote_count: 0,
      current_by_product: [
        { product_id: 1, product_name: 'Asfalto', count: 1, quantity_kg: '1250.500' },
      ],
      current_by_reason: [{ key: 'PRECIO', count: 1, quantity_kg: '1250.500' }],
    }
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = new URL(String(input), 'http://localhost')
        if (url.pathname === '/api/lost-opportunities/statistics') return response(statistics)
        if (url.pathname === '/api/lost-opportunities')
          return response({ items: [lostItem], next_cursor: null })
        if (url.pathname === '/api/lost-opportunities/filter-options')
          return response({
            products: [{ id: 1, name: 'Asfalto', is_active: true }],
            provinces: ['Buenos Aires'],
            responsible_users: [],
          })
        if (url.pathname === '/api/customers')
          return response({
            items: [lostItem.opportunity.customer],
            total: 1,
            page: 1,
            page_size: 100,
          })
        if (url.pathname === '/api/products')
          return response([{ id: 1, name: 'Asfalto', is_active: true }])
        throw new Error(`Unexpected ${url.pathname}`)
      }),
    )
  })

  it('restores Dashboard period dimensions as aware half-open loss filters', async () => {
    window.history.replaceState(
      null,
      '',
      '/lost?period=custom&from=2026-08-01&to=2026-08-31&source=WEB&product=1&province=Buenos+Aires',
    )
    render(<LostPage />)
    await screen.findByText('Constructora Sur')
    const calls = (fetch as ReturnType<typeof vi.fn>).mock.calls.map(([value]) =>
      decodeURIComponent(String(value)),
    )
    expect(calls.some((value) => value.includes('lost_from=2026-08-01T00:00:00-03:00'))).toBe(true)
    expect(calls.some((value) => value.includes('lost_to=2026-09-01T00:00:00-03:00'))).toBe(true)
    expect(calls.some((value) => value.includes('source=WEB'))).toBe(true)
    expect(calls.some((value) => value.includes('product_id=1'))).toBe(true)
  })

  it('renders current losses newest-first with bounded evidence and canonical Lost navigation', async () => {
    render(<LostPage />)
    expect(await screen.findByRole('link', { name: 'Constructora Sur' })).toHaveAttribute(
      'href',
      '/lost/opportunities/8',
    )
    expect(screen.getByText('Reabierta previamente')).toBeInTheDocument()
    expect(screen.getByText(/3 cierres registrados · 1 reapertura/)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Motivos de pérdida' })).toBeInTheDocument()
    expect(screen.getAllByText('Precio').length).toBeGreaterThan(0)
    expect(screen.getByText('Kg cotizados perdidos')).toBeInTheDocument()
    expect(screen.queryByText(/vendedor/i)).not.toBeInTheDocument()
  })

  it('removes the deleted opportunity from Perdidas immediately and retains its filters', async () => {
    window.history.replaceState(null, '', '/lost?source=WEB')
    render(<LostPage selectedOpportunityId={8} />)
    await screen.findByText('Constructora Sur')
    const callsBeforeDelete = (fetch as ReturnType<typeof vi.fn>).mock.calls.length

    fireEvent.click(screen.getByRole('button', { name: 'Simular eliminación perdida' }))

    expect(screen.queryByText('Constructora Sur')).not.toBeInTheDocument()
    await waitFor(() =>
      expect((fetch as ReturnType<typeof vi.fn>).mock.calls.length).toBeGreaterThan(
        callsBeforeDelete,
      ),
    )
    expect(window.location.search).toBe('?source=WEB')
  })

  it('sends only server-supported filters and can reset them', async () => {
    render(<LostPage />)
    await screen.findByText('Constructora Sur')
    fireEvent.change(screen.getByLabelText('Buscar cliente, empresa o ID'), {
      target: { value: 'sur' },
    })
    const moreFilters = screen.getByRole('button', { name: 'Filtros adicionales' })
    expect(moreFilters).toHaveAttribute('aria-expanded', 'false')
    fireEvent.click(moreFilters)
    expect(moreFilters).toHaveAttribute('aria-expanded', 'true')
    fireEvent.change(screen.getByLabelText('Responsable'), { target: { value: 'unassigned' } })
    fireEvent.click(screen.getByLabelText('Precio'))
    fireEvent.click(screen.getByRole('button', { name: 'Aplicar' }))
    await waitFor(() => expect(window.location.search).toContain('reason=PRECIO'))
    expect(moreFilters).toHaveTextContent('(2)')
    expect(window.location.search).toContain('unassigned=true')
    expect(
      (fetch as ReturnType<typeof vi.fn>).mock.calls.some(([url]) =>
        String(url).includes('unassigned=true'),
      ),
    ).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: 'Restablecer' }))
    expect(await screen.findByText('Constructora Sur')).toBeInTheDocument()
  })

  it('filters the results and totals from the reasons ranking', async () => {
    render(<LostPage />)
    const reason = await screen.findByRole('button', { name: /Precio.*100/ })
    fireEvent.click(reason)
    await waitFor(() => expect(window.location.search).toContain('reason=PRECIO'))
    const selected = await screen.findByRole('button', { name: /Precio.*100/, pressed: true })
    expect(screen.getByRole('button', { name: 'Filtros adicionales (1)' })).toBeInTheDocument()
    fireEvent.click(selected)
    await waitFor(() => expect(window.location.search).not.toContain('reason='))
  })

  it('adds cards alongside the table and preserves the selected view when filtering', async () => {
    window.history.replaceState(null, '', '/lost?period=all&source=WEB')
    render(<LostPage />)
    await screen.findByRole('table', { name: 'Oportunidades actualmente perdidas' })
    const fetchCount = (fetch as ReturnType<typeof vi.fn>).mock.calls.length
    fireEvent.click(screen.getByRole('button', { name: 'Fichas' }))
    expect(fetch).toHaveBeenCalledTimes(fetchCount)
    const cards = screen.getByRole('list', { name: 'Fichas de oportunidades perdidas' })
    const card = within(cards).getByRole('link', { name: /Constructora Sur/ })
    expect(card).toHaveAttribute('href', '/lost/opportunities/8?period=all&source=WEB&vista=fichas')
    expect(card).toHaveTextContent('Precio')
    expect(screen.getByRole('heading', { name: 'Motivos de pérdida' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Aplicar' }))
    await screen.findByRole('list', { name: 'Fichas de oportunidades perdidas' })
    expect(window.location.search).toContain('vista=fichas')
    fireEvent.click(screen.getByRole('button', { name: 'Tabla' }))
    expect(
      screen.getByRole('table', { name: 'Oportunidades actualmente perdidas' }),
    ).toBeInTheDocument()
    expect(window.location.search).toBe('?period=all&source=WEB')
  })

  it('compares loss reasons by cases or quoted volume without reloading the results', async () => {
    statistics.current_count = 3
    statistics.without_quote_count = 2
    statistics.current_by_reason.push({ key: 'SIN_RESPUESTA', count: 2, quantity_kg: '0' })
    render(<LostPage />)
    const recommendation = await screen.findByRole('complementary', { name: 'Qué mejorar' })
    expect(recommendation).toHaveTextContent('Sin respuesta · No dejes la venta sin seguimiento')
    expect(screen.queryByRole('heading', { name: 'Productos con más kilos perdidos' })).toBeNull()
    const reason = within(screen.getByRole('region', { name: 'Motivos de pérdida' })).getByRole(
      'button',
      { name: /^Precio/ },
    )
    expect(reason).toHaveTextContent('1 caso')
    const fetchCount = (fetch as ReturnType<typeof vi.fn>).mock.calls.length
    fireEvent.click(screen.getByRole('button', { name: 'Por kilos' }))
    expect(reason).toHaveTextContent('1.250,5 kg')
    expect(reason).not.toHaveTextContent('1 caso')
    expect(recommendation).toHaveTextContent('Precio · Confirmá el presupuesto antes de cotizar')
    expect(fetch).toHaveBeenCalledTimes(fetchCount)
  })

  it.each([
    { noReplyCount: 1, suggestion: 'Revisá los cierres y definí qué ajuste' },
    { noReplyCount: 2, suggestion: 'Sin respuesta · No dejes la venta sin seguimiento' },
  ])(
    'uses cases for the recommendation without quoted kilos ($noReplyCount without reply)',
    async ({ noReplyCount, suggestion }) => {
      statistics.current_count = 1 + noReplyCount
      statistics.current_quantity_kg = '0'
      statistics.without_quote_count = statistics.current_count
      statistics.current_by_product = []
      statistics.current_by_reason = [
        { key: 'PRECIO', count: 1, quantity_kg: '0' },
        { key: 'SIN_RESPUESTA', count: noReplyCount, quantity_kg: '0' },
      ]
      render(<LostPage />)
      const recommendation = await screen.findByRole('complementary', { name: 'Qué mejorar' })
      expect(recommendation).toHaveTextContent(suggestion)
      fireEvent.click(screen.getByRole('button', { name: 'Por kilos' }))
      expect(recommendation).toHaveTextContent(suggestion)
    },
  )

  it('distinguishes an empty filtered result from no current Lost opportunities', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = new URL(String(input), 'http://localhost')
        if (url.pathname === '/api/lost-opportunities/statistics')
          return response({
            current_count: 0,
            current_quantity_kg: '0',
            historical_loss_count: 0,
            historical_quantity_kg: '0',
            reopened_count: 0,
            without_quote_count: 0,
            current_by_product: [],
            current_by_reason: [],
          })
        if (url.pathname === '/api/lost-opportunities')
          return response({ items: [], next_cursor: null })
        if (url.pathname === '/api/lost-opportunities/filter-options')
          return response({
            products: [{ id: 1, name: 'Asfalto', is_active: true }],
            provinces: ['Buenos Aires'],
            responsible_users: [],
          })
        if (url.pathname === '/api/customers')
          return response({ items: [], total: 0, page: 1, page_size: 100 })
        return response([])
      }),
    )
    window.history.replaceState(null, '', '/lost?period=all')
    render(<LostPage />)
    expect(
      await screen.findByRole('heading', { name: 'No hay oportunidades perdidas' }),
    ).toBeInTheDocument()
    expect(screen.queryByRole('complementary', { name: 'Qué mejorar' })).not.toBeInTheDocument()
  })

  it('keeps a safe retry state if the current Lost projection cannot load', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('offline')
      }),
    )
    render(<LostPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No pudimos cargar las oportunidades perdidas',
    )
    expect(screen.getByRole('button', { name: 'Reintentar' })).toBeInTheDocument()
  })

  it('loads the next opaque cursor page without reordering prior rows', async () => {
    const second = {
      ...lostItem,
      loss_event_id: 98,
      opportunity: {
        ...lostItem.opportunity,
        id: 7,
        customer: { ...lostItem.opportunity.customer, name: 'Constructora Norte' },
      },
    }
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = new URL(String(input), 'http://localhost')
        if (url.pathname === '/api/lost-opportunities/statistics')
          return response({
            current_count: 2,
            current_quantity_kg: '1',
            historical_loss_count: 2,
            historical_quantity_kg: '1',
            reopened_count: 0,
            without_quote_count: 0,
            current_by_product: [],
            current_by_reason: [],
          })
        if (url.pathname === '/api/lost-opportunities')
          return response(
            url.searchParams.get('cursor')
              ? { items: [second], next_cursor: null }
              : { items: [lostItem], next_cursor: 'opaque' },
          )
        if (url.pathname === '/api/lost-opportunities/filter-options')
          return response({
            products: [{ id: 1, name: 'Asfalto', is_active: true }],
            provinces: ['Buenos Aires'],
            responsible_users: [],
          })
        if (url.pathname === '/api/customers')
          return response({ items: [], total: 0, page: 1, page_size: 100 })
        return response([])
      }),
    )
    render(<LostPage />)
    await screen.findByText('Constructora Sur')
    fireEvent.click(screen.getByRole('button', { name: 'Cargar más' }))
    expect(await screen.findByText('Constructora Norte')).toBeInTheDocument()
  })

  it('labels a server-authoritative empty result as filtered, not as historical absence', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = new URL(String(input), 'http://localhost')
        if (url.pathname === '/api/lost-opportunities/statistics')
          return response({
            current_count: 0,
            current_quantity_kg: '0',
            historical_loss_count: 1,
            historical_quantity_kg: '1',
            reopened_count: 0,
            without_quote_count: 0,
            current_by_product: [],
            current_by_reason: [],
          })
        if (url.pathname === '/api/lost-opportunities')
          return response(
            url.searchParams.get('search')
              ? { items: [], next_cursor: null }
              : { items: [lostItem], next_cursor: null },
          )
        if (url.pathname === '/api/lost-opportunities/filter-options')
          return response({
            products: [{ id: 1, name: 'Asfalto', is_active: true }],
            provinces: ['Buenos Aires'],
            responsible_users: [],
          })
        if (url.pathname === '/api/customers')
          return response({ items: [], total: 0, page: 1, page_size: 100 })
        return response([])
      }),
    )
    render(<LostPage />)
    await screen.findByText('Constructora Sur')
    fireEvent.change(screen.getByLabelText('Buscar cliente, empresa o ID'), {
      target: { value: 'nadie' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Aplicar' }))
    expect(
      await screen.findByRole('heading', { name: 'No hay pérdidas con estos filtros' }),
    ).toBeInTheDocument()
  })
})
