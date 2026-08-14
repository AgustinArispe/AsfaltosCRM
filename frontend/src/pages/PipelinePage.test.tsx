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

const dndState = vi.hoisted(() => ({ onDragEnd: null as ((event: unknown) => void) | null }))
const logout = vi.hoisted(() => vi.fn())

vi.mock('@dnd-kit/react', () => ({
  PointerSensor: { configure: vi.fn(() => function ConfiguredPointerSensor() {}) },
  KeyboardSensor: { configure: vi.fn(() => function ConfiguredKeyboardSensor() {}) },
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
  useAuth: () => ({ token: 'pipeline-token', logout, user: { role: 'SUPERVISOR' } }),
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
      opportunity('GANADA', 4),
    ]
    mockApi(items)
    const { container } = render(<PipelinePage />)
    await ready()

    for (const status of ['NUEVA', 'COTIZADA', 'NEGOCIACION', 'GANADA'] as const) {
      expect(stage(container, status)).toBeInTheDocument()
    }
    expect(container.querySelector('[data-stage="PERDIDA"]')).not.toBeInTheDocument()
    const card = within(stage(container, 'COTIZADA')).getByRole('button', {
      name: /Abrir oportunidad/,
    })
    expect(card).toHaveTextContent('Empresa 2')
    expect(card).toHaveTextContent('WhatsApp')
    expect(card).not.toHaveTextContent('Vendedor no visible')
    expect(card).not.toHaveTextContent('2500')
    expect(card).not.toHaveTextContent('Buenos Aires')
    expect(card).not.toHaveTextContent('no-mostrar')
    expect(screen.getByText('Legendario')).toBeInTheDocument()
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
    expect(screen.getByText(/Más filtros · 2/)).toBeInTheDocument()

    fireEvent.click(screen.getByText(/Más filtros/))
    fireEvent.change(screen.getByLabelText('Producto'), { target: { value: '10' } })
    expect(within(stage(container, 'COTIZADA')).getByText('Empresa 2')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Limpiar' }))
    await waitFor(() => expect(screen.getByText('Más filtros')).toBeInTheDocument())
  })

  it('keeps time in stage hidden until the optional view setting is enabled', async () => {
    mockApi([opportunity('NUEVA', 1)])
    render(<PipelinePage />)
    await ready()
    expect(screen.queryByText(/En etapa:/)).not.toBeInTheDocument()
    fireEvent.click(screen.getByText('Más filtros'))
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
    fireEvent.change(await within(secondDialog).findByLabelText('Producto'), {
      target: { value: '10' },
    })
    fireEvent.change(within(secondDialog).getByLabelText('Cantidad (kg)'), {
      target: { value: '10' },
    })
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
    fireEvent.change(await within(dialog).findByLabelText('Producto'), {
      target: { value: '10' },
    })
    fireEvent.change(within(dialog).getByLabelText('Cantidad (kg)'), { target: { value: '10' } })
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
})
