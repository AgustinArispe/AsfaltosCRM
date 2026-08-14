import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
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

function response(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}
const lostItem = {
  loss_event_id: 99,
  loss_reason: 'PRECIO',
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
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = new URL(String(input), 'http://localhost')
        if (url.pathname === '/api/lost-opportunities/statistics')
          return response({
            current_count: 1,
            current_quantity_kg: '1250.500',
            historical_loss_count: 3,
            historical_quantity_kg: '2500.500',
            reopened_count: 1,
            by_reason: [],
          })
        if (url.pathname === '/api/lost-opportunities')
          return response({ items: [lostItem], next_cursor: null })
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

  it('renders current losses newest-first with bounded evidence and canonical Lost navigation', async () => {
    render(<LostPage />)
    expect(await screen.findByRole('link', { name: 'Constructora Sur' })).toHaveAttribute(
      'href',
      '/lost/opportunities/8',
    )
    expect(screen.getByText('Reabierta previamente')).toBeInTheDocument()
    expect(screen.getByText('Episodios históricos')).toBeInTheDocument()
    expect(screen.queryByText(/vendedor/i)).not.toBeInTheDocument()
  })

  it('sends only server-supported filters and can reset them', async () => {
    render(<LostPage />)
    await screen.findByText('Constructora Sur')
    fireEvent.change(screen.getByLabelText('Buscar'), { target: { value: 'sur' } })
    fireEvent.click(screen.getByLabelText('Precio'))
    fireEvent.click(screen.getByRole('button', { name: 'Aplicar' }))
    await waitFor(() => expect(screen.getByText('2 filtros activos')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Restablecer' }))
    expect(await screen.findByText('Constructora Sur')).toBeInTheDocument()
  })

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
            by_reason: [],
          })
        if (url.pathname === '/api/lost-opportunities')
          return response({ items: [], next_cursor: null })
        if (url.pathname === '/api/customers')
          return response({ items: [], total: 0, page: 1, page_size: 100 })
        return response([])
      }),
    )
    render(<LostPage />)
    expect(
      await screen.findByRole('heading', { name: 'No hay oportunidades perdidas' }),
    ).toBeInTheDocument()
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
            by_reason: [],
          })
        if (url.pathname === '/api/lost-opportunities')
          return response(
            url.searchParams.get('cursor')
              ? { items: [second], next_cursor: null }
              : { items: [lostItem], next_cursor: 'opaque' },
          )
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
            by_reason: [],
          })
        if (url.pathname === '/api/lost-opportunities')
          return response(
            url.searchParams.get('search')
              ? { items: [], next_cursor: null }
              : { items: [lostItem], next_cursor: null },
          )
        if (url.pathname === '/api/customers')
          return response({ items: [], total: 0, page: 1, page_size: 100 })
        return response([])
      }),
    )
    render(<LostPage />)
    await screen.findByText('Constructora Sur')
    fireEvent.change(screen.getByLabelText('Buscar'), { target: { value: 'nadie' } })
    fireEvent.click(screen.getByRole('button', { name: 'Aplicar' }))
    expect(
      await screen.findByRole('heading', { name: 'No hay pérdidas con estos filtros' }),
    ).toBeInTheDocument()
  })
})
