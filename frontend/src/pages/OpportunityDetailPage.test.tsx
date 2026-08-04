import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { OpportunityDetailPage } from './OpportunityDetailPage'
import type { OpportunityDetail } from '../pipeline/types'

const authState = vi.hoisted(() => ({
  logout: vi.fn(),
}))

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({
    token: 'detail-token',
    logout: authState.logout,
  }),
}))

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function makeDetail(
  overrides: Partial<OpportunityDetail> = {},
): OpportunityDetail {
  return {
    id: 42,
    status: 'GANADA',
    source: 'WEB',
    current_status_entered_at: new Date(Date.now() - 14 * 86_400_000).toISOString(),
    customer: {
      id: 7,
      name: 'Constructora del Sur',
      company: 'Del Sur SA',
      email: 'ventas@delsur.test',
      phone: '+54 11 4444-5555',
      province: 'Buenos Aires',
      legendary_historical_override: true,
    },
    assigned_user: {
      id: 8,
      full_name: 'Martín Vendedor',
      email: 'martin@faa.test',
    },
    products: [
      {
        product: { id: 10, name: 'SuperPhalt', is_active: true },
        quantity_kg: '2500.000',
      },
      {
        product: { id: 11, name: 'Bituplast', is_active: true },
        quantity_kg: '1000.000',
      },
    ],
    created_at: '2026-08-03T17:35:00Z',
    updated_at: '2026-08-12T17:35:00Z',
    loss_reason: null,
    history: [
      {
        id: 1,
        from_status: null,
        to_status: 'NUEVA',
        changed_at: '2026-08-03T17:35:00Z',
        changed_by_user_id: null,
      },
      {
        id: 2,
        from_status: 'NUEVA',
        to_status: 'COTIZADA',
        changed_at: '2026-08-05T17:35:00Z',
        changed_by_user_id: 8,
      },
      {
        id: 3,
        from_status: 'COTIZADA',
        to_status: 'NEGOCIACION',
        changed_at: '2026-08-08T17:35:00Z',
        changed_by_user_id: 8,
      },
      {
        id: 4,
        from_status: 'NEGOCIACION',
        to_status: 'GANADA',
        changed_at: '2026-08-12T17:35:00Z',
        changed_by_user_id: 8,
      },
    ],
    ...overrides,
  }
}

describe('OpportunityDetailPage', () => {
  beforeEach(() => {
    authState.logout.mockReset()
    window.history.replaceState(null, '', '/opportunities/42')
  })

  it('shows a loading state while requesting the opportunity', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(() => undefined)))

    render(<OpportunityDetailPage opportunityId={42} />)

    expect(screen.getByRole('status')).toHaveTextContent(
      'Cargando oportunidad…',
    )
  })

  it('renders customer, commercial data, products, total, history and legendary status', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, makeDetail()))
    vi.stubGlobal('fetch', fetchMock)

    render(<OpportunityDetailPage opportunityId={42} />)

    expect(
      await screen.findByRole('heading', { name: 'Constructora del Sur' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Del Sur SA')).toBeInTheDocument()
    expect(screen.getByText('ventas@delsur.test')).toBeInTheDocument()
    expect(screen.getByText('+54 11 4444-5555')).toBeInTheDocument()
    expect(screen.getByText('Buenos Aires')).toBeInTheDocument()
    expect(screen.getByText('Legendario')).toBeInTheDocument()
    expect(screen.getByText('Ganada')).toBeInTheDocument()
    expect(screen.getByText('Web')).toBeInTheDocument()
    expect(screen.getByText('Martín Vendedor')).toBeInTheDocument()
    expect(screen.getAllByText('3 ago 2026, 14:35')).toHaveLength(2)
    expect(screen.getByText('2 semanas')).toBeInTheDocument()

    const quote = screen.getByRole('heading', { name: 'Cotización' }).parentElement
    expect(quote).not.toBeNull()
    expect(within(quote as HTMLElement).getByText('SuperPhalt')).toBeInTheDocument()
    expect(within(quote as HTMLElement).getByText('Bituplast')).toBeInTheDocument()
    expect(within(quote as HTMLElement).getByText('2.500 kg')).toBeInTheDocument()
    expect(within(quote as HTMLElement).getByText('1.000 kg')).toBeInTheDocument()
    expect(within(quote as HTMLElement).getByText('3.500 kg')).toBeInTheDocument()

    expect(screen.getByText('Consulta creada')).toBeInTheDocument()
    expect(screen.getByText('Estado inicial: Nueva')).toBeInTheDocument()
    expect(screen.getByText('Pasó de Nueva a Cotizada')).toBeInTheDocument()
    expect(screen.getByText('Pasó de Cotizada a Negociación')).toBeInTheDocument()
    expect(screen.getByText('Pasó de Negociación a Ganada')).toBeInTheDocument()
    expect(screen.getAllByRole('listitem')).toHaveLength(4)

    const request = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/opportunities/42')
    expect(new Headers(request.headers).get('Authorization')).toBe(
      'Bearer detail-token',
    )
  })

  it('shows the empty quote state for a new opportunity', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(
          200,
          makeDetail({
            status: 'NUEVA',
            products: [],
            assigned_user: null,
            customer: {
              ...makeDetail().customer,
              legendary_historical_override: false,
            },
            history: [makeDetail().history[0]],
          }),
        ),
      ),
    )

    render(<OpportunityDetailPage opportunityId={42} />)

    expect(
      await screen.findByText('Aún no se registró una cotización.'),
    ).toBeInTheDocument()
    expect(screen.getByText('Sin responsable')).toBeInTheDocument()
    expect(screen.queryByText('Legendario')).not.toBeInTheDocument()
  })

  it('shows a subdued loss reason for a lost opportunity', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(
          200,
          makeDetail({ status: 'PERDIDA', loss_reason: 'PRECIO' }),
        ),
      ),
    )

    render(<OpportunityDetailPage opportunityId={42} />)

    expect(await screen.findByText('Motivo de pérdida')).toBeInTheDocument()
    expect(screen.getByText('Precio')).toBeInTheDocument()
    expect(screen.getByText('Perdida')).toBeInTheDocument()
  })

  it('renders a specific 404 state with a path back to the pipeline', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse(404, { detail: 'Not found' })),
    )

    render(<OpportunityDetailPage opportunityId={999} />)

    expect(
      await screen.findByRole('heading', { name: 'Oportunidad no encontrada' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: 'Volver al Pipeline' }),
    ).toHaveAttribute('href', '/pipeline')
    expect(screen.queryByRole('button', { name: 'Reintentar' })).not.toBeInTheDocument()
  })

  it('offers retry after a network error', async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new TypeError('network unavailable'))
      .mockResolvedValueOnce(jsonResponse(200, makeDetail()))
    vi.stubGlobal('fetch', fetchMock)

    render(<OpportunityDetailPage opportunityId={42} />)

    expect(
      await screen.findByRole('heading', {
        name: 'No pudimos cargar la oportunidad',
      }),
    ).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))

    expect(
      await screen.findByRole('heading', { name: 'Constructora del Sur' }),
    ).toBeInTheDocument()
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
  })

  it('returns to the pipeline with a real keyboard-accessible link', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse(200, makeDetail())),
    )
    render(<OpportunityDetailPage opportunityId={42} />)
    const backLink = await screen.findByRole('link', {
      name: 'Volver al Pipeline',
    })

    backLink.focus()
    expect(backLink).toHaveFocus()
    fireEvent.click(backLink)

    expect(window.location.pathname).toBe('/pipeline')
  })
})
