import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { CustomerDetailPage } from './CustomerDetailPage'
import type { CustomerDetail } from '../customers/types'
import type { OpportunitySummary } from '../pipeline/types'

const authState = vi.hoisted(() => ({ logout: vi.fn() }))

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({ token: 'customer-detail-token', logout: authState.logout }),
}))

const customer: CustomerDetail = {
  id: 7,
  name: 'Constructora del Sur',
  company: 'Del Sur SA',
  email: 'ventas@delsur.test',
  phone: '+54 11 4444-5555',
  province: 'Buenos Aires',
  legendary_historical_override: true,
  created_at: '2026-08-03T17:35:00Z',
}

function makeOpportunity(
  id: number,
  status: OpportunitySummary['status'],
): OpportunitySummary {
  return {
    id,
    status,
    source: id % 2 === 0 ? 'WHATSAPP' : 'WEB',
    current_status_entered_at: '2026-08-04T12:00:00Z',
    customer,
    assigned_user: id === 1 ? null : { id: 9, full_name: 'Martín Vendedor', email: 'martin@faa.test' },
    products:
      status === 'NUEVA'
        ? []
        : [{ product: { id: 10, name: 'SuperPhalt', is_active: true }, quantity_kg: '2500.000' }],
    created_at: id === 1 ? '2026-08-04T12:00:00Z' : '2026-08-03T12:00:00Z',
  }
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function mockDetailApi({
  customerResponse = customer,
  opportunities = [makeOpportunity(1, 'NUEVA'), makeOpportunity(2, 'PERDIDA')],
  customerStatus = 200,
}: {
  customerResponse?: CustomerDetail
  opportunities?: OpportunitySummary[]
  customerStatus?: number
} = {}) {
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = new URL(String(input), 'http://localhost')
      if (url.pathname === '/api/customers/7') {
        return customerStatus === 200
          ? jsonResponse(200, customerResponse)
          : jsonResponse(customerStatus, { detail: 'Not found' })
      }
      if (url.pathname === '/api/opportunities') {
        return jsonResponse(200, {
          items: opportunities,
          page: 1,
          page_size: 100,
          total: opportunities.length,
        })
      }
      throw new Error(`Unexpected request: ${url.pathname}`)
    },
  )
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('CustomerDetailPage', () => {
  beforeEach(() => {
    authState.logout.mockReset()
    window.history.replaceState(null, '', '/customers/7')
  })

  it('loads customer data, registration date, contact links and legendary status', async () => {
    const fetchMock = mockDetailApi()
    render(<CustomerDetailPage customerId={7} />)

    expect(screen.getByRole('status')).toHaveTextContent('Cargando cliente…')
    expect(await screen.findByRole('heading', { name: 'Constructora del Sur' })).toBeInTheDocument()
    expect(screen.getByText('Del Sur SA')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'ventas@delsur.test' })).toHaveAttribute('href', 'mailto:ventas@delsur.test')
    expect(screen.getByRole('link', { name: '+54 11 4444-5555' })).toHaveAttribute('href', 'tel:+541144445555')
    expect(screen.getByText('Buenos Aires')).toBeInTheDocument()
    expect(screen.getByText('Legendario')).toBeInTheDocument()
    expect(screen.getByText('3 ago 2026, 14:35')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Volver a Clientes' })).toHaveAttribute('href', '/customers')

    const detailRequest = fetchMock.mock.calls.find(([input]) => String(input) === '/api/customers/7')
    const request = detailRequest?.[1] as RequestInit
    expect(new Headers(request.headers).get('Authorization')).toBe('Bearer customer-detail-token')
  })

  it('shows all associated opportunities including lost, products and responsible user', async () => {
    mockDetailApi()
    render(<CustomerDetailPage customerId={7} />)
    await screen.findByRole('heading', { name: 'Constructora del Sur' })

    const opportunitiesSection = screen.getByRole('heading', { name: 'Oportunidades' }).parentElement?.parentElement
    expect(opportunitiesSection).not.toBeNull()
    const section = opportunitiesSection as HTMLElement
    expect(within(section).getByText('Nueva')).toBeInTheDocument()
    expect(within(section).getByText('Perdida')).toBeInTheDocument()
    expect(within(section).getByText('SuperPhalt')).toBeInTheDocument()
    expect(within(section).getByText(/2\.500 kg/)).toBeInTheDocument()
    expect(within(section).getByText('Sin cotización')).toBeInTheDocument()
    expect(within(section).getByText('Martín Vendedor')).toBeInTheDocument()
    expect(within(section).getByText('2 oportunidades')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ver detalle de oportunidad 2' })).toHaveAttribute('href', '/opportunities/2')
  })

  it('shows an empty opportunity state without inventing customer categories', async () => {
    mockDetailApi({
      opportunities: [],
      customerResponse: { ...customer, legendary_historical_override: false },
    })
    render(<CustomerDetailPage customerId={7} />)

    expect(await screen.findByText('Este cliente todavía no tiene oportunidades registradas.')).toBeInTheDocument()
    expect(screen.queryByText('Legendario')).not.toBeInTheDocument()
    expect(screen.queryByText('Recurrente')).not.toBeInTheDocument()
  })

  it('renders a specific 404 with a route back to customers', async () => {
    mockDetailApi({ customerStatus: 404 })
    render(<CustomerDetailPage customerId={7} />)

    expect(await screen.findByRole('heading', { name: 'Cliente no encontrado' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Volver a Clientes' })).toHaveAttribute('href', '/customers')
    expect(screen.queryByRole('button', { name: 'Reintentar' })).not.toBeInTheDocument()
  })

  it('offers retry after a network failure and supports keyboard navigation back', async () => {
    let shouldFail = true
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = new URL(String(input), 'http://localhost')
        if (shouldFail) throw new TypeError('network unavailable')
        if (url.pathname === '/api/customers/7') return jsonResponse(200, customer)
        return jsonResponse(200, { items: [], page: 1, page_size: 100, total: 0 })
      }),
    )
    render(<CustomerDetailPage customerId={7} />)
    expect(await screen.findByRole('heading', { name: 'No pudimos cargar el cliente' })).toBeInTheDocument()

    shouldFail = false
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    const backLink = await screen.findByRole('link', { name: 'Volver a Clientes' })
    backLink.focus()
    expect(backLink).toHaveFocus()
    fireEvent.click(backLink)
    await waitFor(() => expect(window.location.pathname).toBe('/customers'))
  })
})
