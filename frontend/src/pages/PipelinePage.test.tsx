import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type {
  OpportunityStatus,
  OpportunitySummary,
  PipelineStatus,
  Product,
} from '../pipeline/types'
import { PipelinePage } from './PipelinePage'

const dndState = vi.hoisted(() => ({
  keyboardConfig: null as Record<string, unknown> | null,
  onDragEnd: null as ((event: unknown) => void) | null,
}))
const logout = vi.hoisted(() => vi.fn())

vi.mock('@dnd-kit/react', () => ({
  PointerSensor: { configure: vi.fn(() => function ConfiguredPointerSensor() {}) },
  KeyboardSensor: {
    configure: vi.fn((config: Record<string, unknown>) => {
      dndState.keyboardConfig = config
      return function ConfiguredKeyboardSensor() {}
    }),
  },
  DragDropProvider: ({
    children,
    onDragEnd,
  }: {
    children: ReactNode
    onDragEnd: (event: unknown) => void
  }) => {
    dndState.onDragEnd = onDragEnd
    return children
  },
  DragOverlay: () => null,
  useDraggable: () => ({ ref: vi.fn(), isDragging: false }),
  useDroppable: () => ({ ref: vi.fn(), isDropTarget: false }),
}))

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({
    token: 'pipeline-token',
    logout,
    user: {
      id: 1,
      full_name: 'Supervisora FAA',
      email: 'supervisora@faa.test',
      role: 'SUPERVISOR',
      is_active: true,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
  }),
}))

const products: Product[] = [
  { id: 10, name: 'SuperPhalt', is_active: true },
  { id: 11, name: 'Bituplast', is_active: true },
]

function opportunity(
  status: OpportunityStatus,
  id: number,
  overrides: Partial<OpportunitySummary> = {},
): OpportunitySummary {
  return {
    id,
    status,
    source: id % 2 === 0 ? 'WHATSAPP' : 'WEB',
    current_status_entered_at: `2026-08-0${id}T12:00:00Z`,
    customer: {
      id: id + 100,
      name: `Cliente ${id}`,
      company: id === 4 ? null : `Empresa ${id}`,
      email: 'no-mostrar@faa.test',
      phone: '+54 11 5555 0101',
      province: 'Buenos Aires',
      legendary_historical_override: false,
      is_legendary: id === 1,
    },
    assigned_user: { id: 8, full_name: 'Vendedor no visible', email: 'seller@faa.test' },
    products: status === 'NUEVA' ? [] : [{ product: products[0], quantity_kg: '2500.000' }],
    created_at: `2026-08-0${id}T12:00:00Z`,
    ...overrides,
  }
}

function response(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function mockApi(items: OpportunitySummary[], transition?: (url: URL) => Response | undefined) {
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = new URL(String(input), 'http://localhost')
      if (url.pathname === '/api/opportunities' && init?.method !== 'POST') {
        const stage = url.searchParams.get('status')
        const source = url.searchParams.get('source')
        const filtered = items.filter(
          (item) => item.status === stage && (!source || item.source === source),
        )
        return response(200, { items: filtered, page: 1, page_size: 100, total: filtered.length })
      }
      if (url.pathname === '/api/products') return response(200, products)
      const custom = transition?.(url)
      if (custom) return custom
      throw new Error(`Unexpected request: ${url.pathname}`)
    },
  )
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function stage(container: HTMLElement, status: PipelineStatus): HTMLElement {
  const element = container.querySelector<HTMLElement>(`[data-stage="${status}"]`)
  if (!element) throw new Error(`Missing ${status}`)
  return element
}

function drop(item: OpportunitySummary, target: PipelineStatus) {
  act(() => {
    dndState.onDragEnd?.({
      canceled: false,
      operation: {
        source: {
          data: {
            opportunityId: item.id,
            customerName: item.customer.name,
            fromStatus: item.status,
            toStatus: target,
          },
        },
        target: { id: target },
      },
    })
  })
}

async function ready() {
  await screen.findByRole('heading', { name: 'Nueva' })
}

describe('PipelinePage', () => {
  beforeEach(() => {
    dndState.onDragEnd = null
    logout.mockReset()
    window.history.replaceState(null, '', '/pipeline')
  })

  it('renders the four active columns, omits Lost, and keeps cards intentionally minimal', async () => {
    const items = [
      opportunity('NUEVA', 1),
      opportunity('COTIZADA', 2),
      opportunity('NEGOCIACION', 3),
      opportunity('GANADA', 4, { current_status_entered_at: new Date().toISOString() }),
    ]
    mockApi(items)
    const { container } = render(<PipelinePage />)
    await ready()

    for (const status of ['NUEVA', 'COTIZADA', 'NEGOCIACION', 'GANADA'] as const) {
      expect(stage(container, status)).toBeInTheDocument()
    }
    expect(container.querySelector('[data-stage="PERDIDA"]')).not.toBeInTheDocument()
    const stageUrls = (fetch as ReturnType<typeof vi.fn>).mock.calls
      .map(([input]) => new URL(String(input), 'http://localhost'))
      .filter((url) => url.pathname === '/api/opportunities')
    expect(stageUrls).toHaveLength(4)
    expect(stageUrls.filter((url) => url.searchParams.get('active_board') === 'true')).toHaveLength(
      1,
    )
    expect(
      stageUrls
        .find((url) => url.searchParams.get('active_board') === 'true')
        ?.searchParams.get('status'),
    ).toBe('GANADA')
    const card = within(stage(container, 'COTIZADA')).getByRole('button', {
      name: /Abrir oportunidad/,
    })
    expect(card).toHaveTextContent('Empresa 2')
    expect(card).toHaveTextContent('WhatsApp')
    expect(card).toHaveAccessibleName(/estado Cotizada/)
    expect(card.querySelector('.pipeline-card__commercial-status')).not.toBeInTheDocument()
    expect(card).not.toHaveTextContent('Vendedor no visible')
    expect(card).not.toHaveTextContent('2500')
    expect(card).not.toHaveTextContent('Buenos Aires')
    expect(card).not.toHaveTextContent('no-mostrar')
    expect(screen.getByText('Legendario')).toBeInTheDocument()
    expect(screen.getByText('Legendario').closest('.pipeline-card__meta')).not.toBeNull()
    expect(stage(container, 'NUEVA').querySelector('[data-icon="document"]')).toBeInTheDocument()
    expect(stage(container, 'COTIZADA').querySelector('[data-icon="coins"]')).toBeInTheDocument()
    expect(
      stage(container, 'NEGOCIACION').querySelector('[data-icon="handshake"]'),
    ).toBeInTheDocument()
    expect(stage(container, 'GANADA').querySelector('[data-icon="trophy"]')).toBeInTheDocument()
  })

  it('preserves keyboard drag controls and keeps Ganada clickable without a drag cursor', async () => {
    const won = opportunity('GANADA', 4, { current_status_entered_at: new Date().toISOString() })
    mockApi([won])
    const { container } = render(<PipelinePage />)
    await ready()

    const keyboardConfig = dndState.keyboardConfig as {
      keyboardCodes: { start: string[]; cancel: string[]; end: string[] }
    }
    expect(keyboardConfig.keyboardCodes).toMatchObject({
      start: ['Space'],
      cancel: ['Escape'],
      end: ['Space', 'Enter', 'Tab'],
    })

    const wonCard = within(stage(container, 'GANADA')).getByRole('button', {
      name: /Abrir oportunidad/,
    })
    expect(wonCard).toHaveClass('cursor-pointer')
    expect(wonCard).not.toHaveClass('cursor-grab')
    expect(wonCard.closest('.pipeline-card')).toHaveClass('pipeline-card--terminal')
    fireEvent.click(wonCard)
    expect(window.location.pathname).toBe('/pipeline/opportunities/4')
  })

  it('uses deterministic identity fallback and opens the canonical CRM-020 route on card activation', async () => {
    const item = opportunity('NUEVA', 4)
    item.customer = { ...item.customer, id: 0, name: '', company: null }
    mockApi([item])
    render(<PipelinePage />)
    await ready()
    const card = screen.getByRole('button', { name: /Cliente #0/ })
    fireEvent.click(card)
    expect(window.location.pathname).toBe('/pipeline/opportunities/4')
  })

  it('shows skeletons, column empties, and no-results distinctly', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => new Promise<Response>(() => undefined)),
    )
    const pending = render(<PipelinePage />)
    expect(screen.getByRole('status', { name: 'Cargando pipeline' })).toBeInTheDocument()
    pending.unmount()

    const item = opportunity('NUEVA', 1)
    mockApi([item])
    render(<PipelinePage />)
    await ready()
    fireEvent.change(screen.getByLabelText('Buscar oportunidades'), {
      target: { value: 'inexistente' },
    })
    await waitFor(() => expect(screen.getByText('Sin resultados')).toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Limpiar filtros' })).toBeInTheDocument()
  })

  it('offers retry after a failed initial load', async () => {
    let shouldFail = true
    const item = opportunity('NUEVA', 1)
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL): Promise<Response> => {
        if (shouldFail) throw new TypeError('network unavailable')
        const url = new URL(String(input), 'http://localhost')
        const stage = url.searchParams.get('status')
        const items = stage === 'NUEVA' ? [item] : []
        return response(200, { items, page: 1, page_size: 100, total: items.length })
      }),
    )
    render(<PipelinePage />)
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No pudimos conectar con el servidor',
    )
    shouldFail = false
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    await ready()
  })

  it('orders each column objectively and supports compact search, source, product, and reset filters', async () => {
    const newest = opportunity('COTIZADA', 3)
    const oldest = opportunity('COTIZADA', 1)
    const whatsapp = opportunity('COTIZADA', 2)
    mockApi([newest, oldest, whatsapp])
    const { container } = render(<PipelinePage />)
    await ready()
    expect(
      within(stage(container, 'COTIZADA')).getAllByRole('button', { name: /Abrir oportunidad/ })[0],
    ).toHaveTextContent('Empresa 3')

    fireEvent.change(screen.getByLabelText('Orden'), { target: { value: 'oldest' } })
    expect(
      within(stage(container, 'COTIZADA')).getAllByRole('button', { name: /Abrir oportunidad/ })[0],
    ).toHaveTextContent('Empresa 1')
    fireEvent.change(screen.getByLabelText('Origen'), { target: { value: 'WHATSAPP' } })
    await waitFor(() =>
      expect(
        within(stage(container, 'COTIZADA')).getAllByRole('button', { name: /Abrir oportunidad/ }),
      ).toHaveLength(1),
    )
    expect(screen.getByText(/Filtros · 2/)).toBeInTheDocument()

    fireEvent.click(screen.getByText(/Filtros/))
    fireEvent.change(screen.getByLabelText('Producto'), { target: { value: '10' } })
    expect(within(stage(container, 'COTIZADA')).getByText('Empresa 2')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Limpiar' }))
    await waitFor(() => expect(screen.getByText('Filtros')).toBeInTheDocument())
  })

  it('keeps time in stage hidden until the optional view setting is enabled', async () => {
    mockApi([opportunity('NUEVA', 1)])
    render(<PipelinePage />)
    await ready()
    expect(screen.queryByText(/En etapa:/)).not.toBeInTheDocument()
    fireEvent.click(screen.getByText('Filtros'))
    fireEvent.click(screen.getByLabelText('Mostrar antigüedad de etapa'))
    expect(screen.getByText(/En etapa:/)).toBeInTheDocument()
  })

  it('moves only valid transitions, rolls back rejected mutations, and ignores same-column drops', async () => {
    const quoted = opportunity('COTIZADA', 2)
    const fetchMock = mockApi([quoted], (url) =>
      url.pathname.endsWith('/move-to-negotiation')
        ? response(409, { detail: 'Invalid transition' })
        : undefined,
    )
    const { container } = render(<PipelinePage />)
    await ready()
    const callsBeforeSameColumn = fetchMock.mock.calls.length
    drop(quoted, 'COTIZADA')
    expect(fetchMock).toHaveBeenCalledTimes(callsBeforeSameColumn)
    drop(quoted, 'GANADA')
    expect(fetchMock).toHaveBeenCalledTimes(callsBeforeSameColumn)
    drop(quoted, 'NEGOCIACION')
    expect(await screen.findByRole('alert')).toHaveTextContent('se mantuvo sin cambios')
    expect(within(stage(container, 'COTIZADA')).getByText('Empresa 2')).toBeInTheDocument()
  })

  it('optimistically moves a valid DnD transition and reconciles the authoritative response', async () => {
    const quoted = opportunity('COTIZADA', 2)
    const moved = { ...quoted, status: 'NEGOCIACION' as const }
    const fetchMock = mockApi([quoted], (url) =>
      url.pathname.endsWith('/move-to-negotiation') ? response(200, moved) : undefined,
    )
    const { container } = render(<PipelinePage />)
    await ready()
    drop(quoted, 'NEGOCIACION')
    await waitFor(() =>
      expect(within(stage(container, 'NEGOCIACION')).getByText('Empresa 2')).toBeInTheDocument(),
    )
    expect(
      fetchMock.mock.calls.some(([input]) => String(input).endsWith('/move-to-negotiation')),
    ).toBe(true)
  })

  it('uses the shared quote flow for NUEVA to COTIZADA and reconciles cancellation or rejection', async () => {
    const item = opportunity('NUEVA', 1)
    mockApi([item], (url) =>
      url.pathname.endsWith('/quote')
        ? response(409, { detail: 'Product is inactive' })
        : undefined,
    )
    const { container } = render(<PipelinePage />)
    await ready()
    drop(item, 'COTIZADA')
    const dialog = await screen.findByRole('dialog', { name: 'Cotizar oportunidad' })
    expect(within(stage(container, 'NUEVA')).getByText('Empresa 1')).toBeInTheDocument()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Cancelar' }))
    expect(screen.queryByRole('dialog', { name: 'Cotizar oportunidad' })).not.toBeInTheDocument()

    drop(item, 'COTIZADA')
    const secondDialog = await screen.findByRole('dialog', { name: 'Cotizar oportunidad' })
    fireEvent.click(await within(secondDialog).findByRole('radio', { name: 'SuperPhalt' }))
    fireEvent.click(within(secondDialog).getByRole('button', { name: 'Continuar con cantidad' }))
    fireEvent.change(within(secondDialog).getByLabelText('Cantidad (kg)'), {
      target: { value: '10' },
    })
    fireEvent.click(within(secondDialog).getByRole('button', { name: 'Agregar producto' }))
    fireEvent.click(within(secondDialog).getByRole('button', { name: 'Revisar y confirmar' }))
    fireEvent.click(within(secondDialog).getByRole('button', { name: 'Confirmar cotización' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('ya no está activo')
    expect(within(stage(container, 'NUEVA')).getByText('Empresa 1')).toBeInTheDocument()
  })

  it('reconciles a successful quote without reloading the whole Pipeline', async () => {
    const item = opportunity('NUEVA', 1)
    const quoted = {
      ...item,
      status: 'COTIZADA' as const,
      products: [{ product: products[0], quantity_kg: '10.000' }],
    }
    const fetchMock = mockApi([item], (url) =>
      url.pathname.endsWith('/quote') ? response(200, quoted) : undefined,
    )
    const { container } = render(<PipelinePage />)
    await ready()
    drop(item, 'COTIZADA')
    const dialog = await screen.findByRole('dialog', { name: 'Cotizar oportunidad' })
    fireEvent.click(await within(dialog).findByRole('radio', { name: 'SuperPhalt' }))
    fireEvent.click(within(dialog).getByRole('button', { name: 'Continuar con cantidad' }))
    fireEvent.change(within(dialog).getByLabelText('Cantidad (kg)'), { target: { value: '10' } })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Agregar producto' }))
    fireEvent.click(within(dialog).getByRole('button', { name: 'Revisar y confirmar' }))
    fireEvent.click(within(dialog).getByRole('button', { name: 'Confirmar cotización' }))
    await waitFor(() =>
      expect(within(stage(container, 'COTIZADA')).getByText('Empresa 1')).toBeInTheDocument(),
    )
    expect(
      fetchMock.mock.calls.filter(([input]) => String(input).includes('/api/opportunities?'))
        .length,
    ).toBe(4)
  })

  it('does not make per-card requests and marks server-backed source filtering in the list query', async () => {
    const fetchMock = mockApi([opportunity('NUEVA', 1), opportunity('COTIZADA', 2)])
    render(<PipelinePage />)
    await ready()
    expect(
      fetchMock.mock.calls.filter(([input]) => String(input).includes('/api/opportunities')).length,
    ).toBe(4)
    fireEvent.change(screen.getByLabelText('Origen'), { target: { value: 'WEB' } })
    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([input]) => String(input).includes('source=WEB'))).toBe(
        true,
      ),
    )
  })

  it('creates a manual opportunity without reloading stages and reveals it only on explicit action', async () => {
    const referred = opportunity('NUEVA', 9, {
      source: 'REFERIDO',
      customer: {
        ...opportunity('NUEVA', 9).customer,
        name: 'Cliente referido',
        company: 'Referidos del Sur',
      },
    })
    const items: OpportunitySummary[] = [opportunity('NUEVA', 1)]
    const fetchMock = mockApi(items, (url) => {
      if (url.pathname === '/api/users') return response(200, [])
      if (url.pathname === '/api/opportunities/manual') {
        items.push(referred)
        return response(201, { created: true, opportunity: { ...referred, history: [] } })
      }
      return undefined
    })
    const { container } = render(<PipelinePage />)
    await ready()
    fireEvent.change(screen.getByLabelText('Buscar oportunidades'), {
      target: { value: 'otra búsqueda' },
    })
    await waitFor(() => expect(screen.getByText('Sin resultados')).toBeInTheDocument())
    const stageRequestsBeforeCreate = fetchMock.mock.calls.filter(([input]) =>
      String(input).includes('/api/opportunities?'),
    ).length

    fireEvent.click(screen.getByRole('button', { name: 'Nueva oportunidad' }))
    const dialog = await screen.findByRole('dialog', { name: 'Nueva oportunidad' })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Cliente nuevo' }))
    fireEvent.change(within(dialog).getByLabelText('Nombre *'), {
      target: { value: 'Cliente referido' },
    })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Crear oportunidad' }))

    expect(
      await screen.findAllByText('Oportunidad creada. Los filtros actuales la están ocultando.'),
    ).toHaveLength(2)
    expect(
      fetchMock.mock.calls.filter(([input]) => String(input).includes('/api/opportunities?')),
    ).toHaveLength(stageRequestsBeforeCreate)
    expect(container.querySelector('[data-stage="NUEVA"]')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Ver en Nueva' }))
    await waitFor(() =>
      expect(within(stage(container, 'NUEVA')).getByText('Referidos del Sur')).toBeInTheDocument(),
    )
    expect(screen.getByLabelText('Buscar oportunidades')).toHaveValue('')
  })

  it('offers Referido in the Pipeline source filter', async () => {
    mockApi([])
    render(<PipelinePage />)
    await ready()
    expect(screen.getByRole('option', { name: 'Manual' })).toHaveValue('REFERIDO')
  })

  it('keeps failed-stage data and reports a truthful partial manual refresh', async () => {
    const item = opportunity('COTIZADA', 2)
    let refresh = false
    const fetchMock = vi.fn(async (input: RequestInfo | URL): Promise<Response> => {
      const url = new URL(String(input), 'http://localhost')
      const status = url.searchParams.get('status')
      if (refresh && status === 'COTIZADA') throw new TypeError('network unavailable')
      const items = status === 'COTIZADA' ? [item] : []
      return response(200, { items, page: 1, page_size: 100, total: items.length })
    })
    vi.stubGlobal('fetch', fetchMock)
    const { container } = render(<PipelinePage />)
    await ready()
    const board = container.querySelector('.pipeline-board')
    refresh = true
    fireEvent.click(screen.getByRole('button', { name: 'Actualizar' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'La actualización fue parcial. No pudimos actualizar: Cotizada.',
    )
    expect(within(stage(container, 'COTIZADA')).getByText('Empresa 2')).toBeInTheDocument()
    expect(container.querySelector('.pipeline-board')).toBe(board)
    expect(fetchMock).toHaveBeenCalledTimes(8)
  })

  it('expires simultaneous GANADA cards with one narrow server reconciliation', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-09-08T15:00:00Z'))
    try {
      const expiresSoon = '2026-08-09T15:00:01Z'
      const wonItems = [
        opportunity('GANADA', 4, { current_status_entered_at: expiresSoon }),
        opportunity('GANADA', 5, { current_status_entered_at: expiresSoon }),
      ]
      let wonRequests = 0
      const fetchMock = vi.fn(async (input: RequestInfo | URL): Promise<Response> => {
        const url = new URL(String(input), 'http://localhost')
        const status = url.searchParams.get('status')
        if (status === 'GANADA') wonRequests += 1
        const items = status === 'GANADA' && wonRequests === 1 ? wonItems : []
        return response(200, { items, page: 1, page_size: 100, total: items.length })
      })
      vi.stubGlobal('fetch', fetchMock)
      let container!: HTMLElement
      await act(async () => {
        ;({ container } = render(<PipelinePage />))
      })
      expect(within(stage(container, 'GANADA')).getAllByRole('button')).toHaveLength(2)

      await act(async () => {
        await vi.advanceTimersByTimeAsync(1_000)
      })

      expect(within(stage(container, 'GANADA')).queryAllByRole('button')).toHaveLength(0)
      const stageCalls = fetchMock.mock.calls.map(([input]) =>
        new URL(String(input), 'http://localhost').searchParams.get('status'),
      )
      expect(stageCalls.filter((status) => status === 'GANADA')).toHaveLength(2)
      expect(stageCalls.filter((status) => status !== 'GANADA')).toHaveLength(3)
    } finally {
      vi.useRealTimers()
    }
  })

  it('recovers from focus with only a GANADA reconciliation', async () => {
    const won = opportunity('GANADA', 4, {
      current_status_entered_at: new Date(Date.now() - 86_400_000).toISOString(),
    })
    let wonRequests = 0
    const fetchMock = vi.fn(async (input: RequestInfo | URL): Promise<Response> => {
      const url = new URL(String(input), 'http://localhost')
      const status = url.searchParams.get('status')
      if (status === 'GANADA') wonRequests += 1
      const items = status === 'GANADA' && wonRequests === 1 ? [won] : []
      return response(200, { items, page: 1, page_size: 100, total: items.length })
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<PipelinePage />)
    await ready()

    act(() => window.dispatchEvent(new Event('focus')))
    await waitFor(() => expect(wonRequests).toBe(2))

    const stageCalls = fetchMock.mock.calls.map(([input]) =>
      new URL(String(input), 'http://localhost').searchParams.get('status'),
    )
    expect(stageCalls.filter((status) => status === 'GANADA')).toHaveLength(2)
    expect(stageCalls.filter((status) => status !== 'GANADA')).toHaveLength(3)
  })
})
