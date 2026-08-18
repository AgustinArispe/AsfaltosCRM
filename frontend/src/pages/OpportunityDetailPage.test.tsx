import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { OpportunityDetail } from '../pipeline/types'
import { OpportunityDetailPage } from './OpportunityDetailPage'

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

function makeDetail(overrides: Partial<OpportunityDetail> = {}): OpportunityDetail {
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
    vi.stubGlobal(
      'fetch',
      vi.fn(() => new Promise<Response>(() => undefined)),
    )

    render(<OpportunityDetailPage opportunityId={42} />)

    expect(screen.getByRole('status')).toHaveTextContent('Cargando oportunidad…')
  })

  it('renders customer, commercial data, products, total, history and legendary status', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, makeDetail()))
    vi.stubGlobal('fetch', fetchMock)

    render(<OpportunityDetailPage opportunityId={42} />)

    expect(await screen.findByRole('heading', { name: 'Del Sur SA' })).toBeInTheDocument()
    expect(screen.getByText('Contacto: Constructora del Sur')).toBeInTheDocument()
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
    expect(new Headers(request.headers).get('Authorization')).toBe('Bearer detail-token')
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

    expect(await screen.findByText('Aún no se registró una cotización.')).toBeInTheDocument()
    expect(screen.getByText('Sin responsable')).toBeInTheDocument()
    expect(screen.queryByText('Legendario')).not.toBeInTheDocument()
  })

  it('shows a subdued loss reason for a lost opportunity', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          jsonResponse(200, makeDetail({ status: 'PERDIDA', loss_reason: 'PRECIO' })),
        ),
    )

    render(<OpportunityDetailPage opportunityId={42} />)

    expect(await screen.findByText('Motivo de pérdida')).toBeInTheDocument()
    expect(screen.getAllByText('Precio')[0]).toBeInTheDocument()
    expect(screen.getByText('Perdida')).toBeInTheDocument()
  })

  it('renders a specific 404 state with a path back to the pipeline', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(404, { detail: 'Not found' })))

    render(<OpportunityDetailPage opportunityId={999} />)

    expect(
      await screen.findByRole('heading', { name: 'Oportunidad no encontrada' }),
    ).toBeInTheDocument()
    expect(screen.getByText(/La oportunidad no está disponible/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Volver al Pipeline' })).toHaveAttribute(
      'href',
      '/pipeline',
    )
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

    expect(await screen.findByRole('heading', { name: 'Del Sur SA' })).toBeInTheDocument()
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
  })

  it('returns to the pipeline with a real keyboard-accessible link', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(200, makeDetail())))
    render(<OpportunityDetailPage opportunityId={42} />)
    const backLink = await screen.findByRole('link', {
      name: 'Volver al Pipeline',
    })

    backLink.focus()
    expect(backLink).toHaveFocus()
    fireEvent.click(backLink)

    expect(window.location.pathname).toBe('/pipeline')
  })

  it('loads Notes only when opened and saves a multiline Note with Ctrl+Enter', async () => {
    const note = {
      id: 5,
      opportunity_id: 42,
      author_user_id: 8,
      author_name: 'Martín Vendedor',
      created_at: '2026-08-12T18:00:00Z',
      current_revision: {
        id: 6,
        revision_number: 1,
        body: 'Seguimiento interno',
        is_pinned: false,
        actor_user_id: 8,
        actor_name: 'Martín Vendedor',
        created_at: '2026-08-12T18:00:00Z',
      },
    }
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(200, makeDetail()))
      .mockResolvedValueOnce(jsonResponse(200, { items: [note], next_cursor: null }))
      .mockResolvedValueOnce(jsonResponse(201, note))
    vi.stubGlobal('fetch', fetchMock)

    render(<OpportunityDetailPage opportunityId={42} />)
    await screen.findByRole('heading', { name: 'Del Sur SA' })
    expect(fetchMock).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: 'Notas' }))
    expect(await screen.findByText('Seguimiento interno')).toBeInTheDocument()
    const composer = screen.getByLabelText('Agregar nota')
    fireEvent.change(composer, { target: { value: 'Primera línea\nSegunda línea' } })
    fireEvent.keyDown(composer, { key: 'Enter' })
    expect(composer).toHaveValue('Primera línea\nSegunda línea')
    fireEvent.keyDown(composer, { key: 'Enter', ctrlKey: true })
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3))
    expect(fetchMock.mock.calls[2]?.[0]).toBe('/api/opportunities/42/notes')
    expect(screen.getByText('Seguimiento interno')).toBeInTheDocument()
  })

  it('preserves a Note draft after a recoverable save failure', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(200, makeDetail()))
      .mockResolvedValueOnce(jsonResponse(200, { items: [], next_cursor: null }))
      .mockRejectedValueOnce(new TypeError('network'))
    vi.stubGlobal('fetch', fetchMock)
    render(<OpportunityDetailPage opportunityId={42} />)
    await screen.findByRole('heading', { name: 'Del Sur SA' })
    fireEvent.click(screen.getByRole('button', { name: 'Notas' }))
    await screen.findByText('Aún no hay notas.')
    const composer = screen.getByLabelText('Agregar nota')
    fireEvent.change(composer, { target: { value: 'No perder esta nota' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar nota' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('No pudimos guardar la nota')
    expect(composer).toHaveValue('No perder esta nota')
  })

  it('shows Reopen only for a lost opportunity with a retained quote and routes after success', async () => {
    const reopened = makeDetail({ status: 'NEGOCIACION' })
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse(200, makeDetail({ status: 'PERDIDA', loss_reason: 'PRECIO' })),
      )
      .mockResolvedValueOnce(jsonResponse(200, reopened))
    vi.stubGlobal('fetch', fetchMock)
    render(<OpportunityDetailPage opportunityId={42} surface='lost' />)
    expect(await screen.findByRole('button', { name: 'Reabrir' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Reabrir' }))
    expect(screen.getByRole('heading', { name: 'Reabrir oportunidad' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Reabrir en negociación' }))
    await waitFor(() => expect(window.location.pathname).toBe('/pipeline/opportunities/42'))
    expect(fetchMock.mock.calls[1]?.[0]).toBe('/api/opportunities/42/reopen')
  })

  it('does not offer Reopen when a lost opportunity has no retained quote', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          jsonResponse(200, makeDetail({ status: 'PERDIDA', products: [], loss_reason: 'PRECIO' })),
        ),
    )
    render(<OpportunityDetailPage opportunityId={42} surface='lost' />)
    await screen.findByText('Motivo de pérdida')
    expect(screen.queryByRole('button', { name: 'Reabrir' })).not.toBeInTheDocument()
  })

  it('exposes the applicable commercial actions and confirms a new quote without changing status first', async () => {
    const newDetail = makeDetail({
      status: 'NUEVA',
      products: [],
      history: [makeDetail().history[0]],
    })
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(200, newDetail))
      .mockResolvedValueOnce(jsonResponse(200, [{ id: 10, name: 'SuperPhalt', is_active: true }]))
      .mockResolvedValueOnce(
        jsonResponse(200, { ...newDetail, status: 'COTIZADA', products: makeDetail().products }),
      )
      .mockResolvedValueOnce(jsonResponse(200, makeDetail({ status: 'COTIZADA' })))
    vi.stubGlobal('fetch', fetchMock)
    render(<OpportunityDetailPage opportunityId={42} />)
    await screen.findByRole('heading', { name: 'Del Sur SA' })
    expect(screen.getByRole('button', { name: 'Cotizar' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Marcar perdida' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Cotizar' }))
    const product = await screen.findByLabelText('Producto')
    fireEvent.change(product, { target: { value: '10' } })
    fireEvent.click(screen.getByRole('button', { name: 'Continuar con cantidad' }))
    fireEvent.change(screen.getByLabelText('Cantidad (kg)'), { target: { value: '1000' } })
    fireEvent.click(screen.getByRole('button', { name: 'Agregar producto' }))
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar cotización' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(4))
    expect(fetchMock.mock.calls[2]?.[0]).toBe('/api/opportunities/42/quote')
  })

  it('guides quote keyboard progression and protects a dirty review from dismissal', async () => {
    const newDetail = makeDetail({ status: 'NUEVA', products: [] })
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(jsonResponse(200, newDetail))
        .mockResolvedValueOnce(
          jsonResponse(200, [{ id: 10, name: 'SuperPhalt', is_active: true }]),
        ),
    )
    render(<OpportunityDetailPage opportunityId={42} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Cotizar' }))
    const product = await screen.findByLabelText('Producto')
    expect(product).toHaveFocus()
    fireEvent.change(product, { target: { value: '10' } })
    fireEvent.keyDown(product, { key: 'Enter' })
    const quantity = screen.getByLabelText('Cantidad (kg)')
    expect(quantity).toHaveFocus()
    fireEvent.change(quantity, { target: { value: '1250' } })
    fireEvent.keyDown(quantity, { key: 'Enter' })
    expect(screen.getByRole('heading', { name: 'Revisá la cotización' })).toBeInTheDocument()
    expect(screen.getAllByText('1.250 kg')).toHaveLength(2)

    fireEvent.click(screen.getByRole('button', { name: 'Cerrar cotizar oportunidad' }))
    expect(screen.getByRole('heading', { name: '¿Descartar los cambios?' })).toBeInTheDocument()
    const continueEditing = screen.getByRole('button', { name: 'Seguir editando' })
    expect(continueEditing).toHaveFocus()
    fireEvent.click(continueEditing)
    const reviewHeading = screen.getByRole('heading', { name: 'Revisá la cotización' })
    expect(reviewHeading).toBeInTheDocument()
    expect(reviewHeading).toHaveFocus()
  })

  it('shows quote edit and forward-transition actions only in eligible active states', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(200, makeDetail({ status: 'COTIZADA' })))
      .mockResolvedValueOnce(jsonResponse(200, makeDetail({ status: 'NEGOCIACION' })))
    vi.stubGlobal('fetch', fetchMock)
    render(<OpportunityDetailPage opportunityId={42} />)
    await screen.findByRole('heading', { name: 'Del Sur SA' })
    expect(screen.getByRole('button', { name: 'Editar cotización' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Pasar a negociación' }))
    await waitFor(() =>
      expect(fetchMock.mock.calls[1]?.[0]).toBe('/api/opportunities/42/move-to-negotiation'),
    )
  })

  it('navigates to the exact internal WhatsApp conversation and never uses an external fallback', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(200, makeDetail()))
      .mockResolvedValueOnce(
        jsonResponse(200, {
          items: [
            {
              id: 73,
              external_phone: '+54 11 4444-5555',
              customer: { id: 7 },
            },
          ],
          next_page_cursor: null,
          sync_cursor: 'cursor',
        }),
      )
    vi.stubGlobal('fetch', fetchMock)
    render(<OpportunityDetailPage opportunityId={42} />)
    await screen.findByRole('heading', { name: 'Del Sur SA' })
    fireEvent.click(screen.getByRole('button', { name: 'Abrir WhatsApp' }))
    await waitFor(() => expect(window.location.pathname).toBe('/whatsapp/conversations/73'))
    expect(
      document.querySelector('a[href^="https://wa.me"], a[href^="https://api.whatsapp.com"]'),
    ).toBeNull()
  })

  it('explains when no internal WhatsApp conversation can be verified', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(200, makeDetail()))
      .mockImplementation(() =>
        Promise.resolve(
          jsonResponse(200, { items: [], next_page_cursor: null, sync_cursor: 'cursor' }),
        ),
      )
    vi.stubGlobal('fetch', fetchMock)
    render(<OpportunityDetailPage opportunityId={42} />)
    await screen.findByRole('heading', { name: 'Del Sur SA' })
    fireEvent.click(screen.getByRole('button', { name: 'Abrir WhatsApp' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No existe una conversación interna vinculada',
    )
  })
})
