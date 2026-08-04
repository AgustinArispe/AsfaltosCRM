import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { PipelinePage } from './PipelinePage'
import type {
  OpportunitySummary,
  OpportunityStatus,
  PipelineStatus,
  Product,
} from '../pipeline/types'

const dndState = vi.hoisted(() => ({
  onDragEnd: null as ((event: unknown) => void) | null,
}))

const authState = vi.hoisted(() => ({
  role: 'SUPERVISOR' as 'SUPERVISOR' | 'VENDEDOR',
  logout: vi.fn(),
}))

vi.mock('@dnd-kit/react', () => ({
  PointerSensor: class PointerSensor {},
  KeyboardSensor: {
    configure: vi.fn(() => class ConfiguredKeyboardSensor {}),
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
  useDraggable: () => ({
    ref: vi.fn(),
    handleRef: vi.fn(),
    isDragging: false,
    isDropping: false,
    isDragSource: false,
    draggable: {},
  }),
  useDroppable: () => ({
    ref: vi.fn(),
    isDropTarget: false,
    droppable: {},
  }),
}))

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({
    token: 'pipeline-token',
    logout: authState.logout,
    user: { role: authState.role },
  }),
}))

const activeProducts: Product[] = [
  { id: 10, name: 'SuperPhalt', is_active: true },
  { id: 11, name: 'Bituplast', is_active: true },
]

function makeOpportunity(
  status: OpportunityStatus,
  id = 1,
): OpportunitySummary {
  return {
    id,
    status,
    source: 'WEB',
    current_status_entered_at: '2026-08-01T12:00:00Z',
    customer: {
      id: id + 100,
      name: `Cliente ${status}`,
      company: 'Constructora FAA',
      email: null,
      phone: null,
      province: null,
      legendary_historical_override: false,
    },
    assigned_user: {
      id: 8,
      full_name: 'Martín Vendedor',
      email: 'martin@faa.test',
    },
    products:
      status === 'NUEVA'
        ? []
        : [
            {
              product: activeProducts[0],
              quantity_kg: '2500.000',
            },
          ],
    created_at: '2026-08-01T12:00:00Z',
  }
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function movedOpportunity(
  opportunity: OpportunitySummary,
  status: OpportunityStatus,
  products = opportunity.products,
): OpportunitySummary {
  return {
    ...opportunity,
    status,
    products,
    current_status_entered_at: '2026-08-04T15:00:00Z',
  }
}

type ApiMockOptions = {
  opportunities?: OpportunitySummary[]
  products?: Product[]
  failLoad?: () => boolean
  actionResponse?: (
    url: URL,
    init: RequestInit | undefined,
  ) => Response | Promise<Response> | undefined
}

function mockApi({
  opportunities = [],
  products = activeProducts,
  failLoad,
  actionResponse,
}: ApiMockOptions = {}) {
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = new URL(String(input), 'http://localhost')

      if (url.pathname === '/api/opportunities' && init?.method !== 'POST') {
        if (failLoad?.()) throw new TypeError('network unavailable')
        const status = url.searchParams.get('status')
        const items = opportunities.filter(
          (opportunity) => opportunity.status === status,
        )
        return jsonResponse(200, {
          items,
          page: Number(url.searchParams.get('page')),
          page_size: 100,
          total: items.length,
        })
      }

      if (url.pathname === '/api/products') {
        return jsonResponse(200, products)
      }

      const customResponse = actionResponse?.(url, init)
      if (customResponse) return customResponse
      throw new Error(`Unexpected request: ${url.pathname}`)
    },
  )
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function getStage(container: HTMLElement, status: PipelineStatus): HTMLElement {
  const stage = container.querySelector<HTMLElement>(`[data-stage="${status}"]`)
  if (!stage) throw new Error(`Missing stage ${status}`)
  return stage
}

function simulateDrop(
  opportunity: OpportunitySummary,
  targetStatus: PipelineStatus,
) {
  const nextByStatus: Partial<Record<PipelineStatus, PipelineStatus>> = {
    NUEVA: 'COTIZADA',
    COTIZADA: 'NEGOCIACION',
    NEGOCIACION: 'GANADA',
  }
  act(() => {
    dndState.onDragEnd?.({
      canceled: false,
      operation: {
        source: {
          id: opportunity.id,
          data: {
            opportunityId: opportunity.id,
            customerName: opportunity.customer.name,
            fromStatus: opportunity.status,
            toStatus: nextByStatus[opportunity.status as PipelineStatus],
          },
        },
        target: { id: targetStatus },
      },
    })
  })
}

async function waitForPipeline() {
  await screen.findByRole('heading', { name: 'Nuevos' })
}

describe('PipelinePage', () => {
  beforeEach(() => {
    dndState.onDragEnd = null
    authState.role = 'SUPERVISOR'
    authState.logout.mockReset()
  })

  it('renders configured columns, counters, reusable cards, and empty states', async () => {
    const newOpportunity = makeOpportunity('NUEVA', 1)
    const quotedOpportunity = makeOpportunity('COTIZADA', 2)
    mockApi({ opportunities: [newOpportunity, quotedOpportunity] })
    const { container } = render(<PipelinePage />)

    await waitForPipeline()
    expect(screen.getByRole('heading', { name: 'Cotizados' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Negociación' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Ganados' })).toBeInTheDocument()

    expect(
      within(getStage(container, 'NUEVA')).getByLabelText('1 oportunidad'),
    ).toHaveTextContent('1')
    expect(within(getStage(container, 'NUEVA')).getByText('Cliente NUEVA')).toBeInTheDocument()
    expect(within(getStage(container, 'COTIZADA')).getByText('SuperPhalt')).toBeInTheDocument()
    expect(within(getStage(container, 'NEGOCIACION')).getByText('No hay oportunidades')).toBeInTheDocument()
    expect(within(getStage(container, 'GANADA')).getByText('No hay oportunidades')).toBeInTheDocument()
  })

  it('shows the initial loading state', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(() => undefined)))
    render(<PipelinePage />)

    expect(screen.getByRole('status')).toHaveTextContent('Cargando pipeline…')
  })

  it('offers retry after a loading error', async () => {
    let shouldFail = true
    mockApi({ failLoad: () => shouldFail })
    render(<PipelinePage />)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No pudimos conectar con el servidor',
    )
    shouldFail = false
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))

    await waitForPipeline()
  })

  it('opens quote modal on NUEVA drop and does not move before confirmation', async () => {
    const opportunity = makeOpportunity('NUEVA')
    mockApi({ opportunities: [opportunity] })
    const { container } = render(<PipelinePage />)
    await waitForPipeline()

    simulateDrop(opportunity, 'COTIZADA')

    expect(
      await screen.findByRole('dialog', { name: 'Cotizar oportunidad' }),
    ).toBeInTheDocument()
    expect(within(getStage(container, 'NUEVA')).getByText('Cliente NUEVA')).toBeInTheDocument()
    expect(within(getStage(container, 'COTIZADA')).queryByText('Cliente NUEVA')).not.toBeInTheDocument()
    expect(await screen.findByLabelText('Producto')).toHaveFocus()
  })

  it('validates duplicate products and quantities, then quotes multiple products', async () => {
    const opportunity = makeOpportunity('NUEVA')
    const fetchMock = mockApi({
      opportunities: [opportunity],
      actionResponse: (url) => {
        if (url.pathname.endsWith('/quote')) {
          return jsonResponse(
            200,
            movedOpportunity(opportunity, 'COTIZADA', [
              { product: activeProducts[0], quantity_kg: '2500.000' },
              { product: activeProducts[1], quantity_kg: '1000.000' },
            ]),
          )
        }
      },
    })
    const { container } = render(<PipelinePage />)
    await waitForPipeline()

    simulateDrop(opportunity, 'COTIZADA')
    const firstProduct = await screen.findByLabelText('Producto')
    fireEvent.change(firstProduct, { target: { value: '10' } })
    fireEvent.change(screen.getByLabelText('Cantidad (kg)'), {
      target: { value: '2500' },
    })
    fireEvent.click(screen.getByRole('button', { name: '+ Agregar producto' }))

    const productSelects = screen.getAllByLabelText('Producto')
    const quantityInputs = screen.getAllByLabelText('Cantidad (kg)')
    fireEvent.change(productSelects[1], { target: { value: '10' } })
    fireEvent.change(quantityInputs[1], { target: { value: '0' } })
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar cotización' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Revisá los productos y cantidades',
    )

    fireEvent.change(productSelects[1], { target: { value: '11' } })
    fireEvent.change(quantityInputs[1], { target: { value: '1000' } })
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar cotización' }))

    await waitFor(() =>
      expect(within(getStage(container, 'COTIZADA')).getByText('Cliente NUEVA')).toBeInTheDocument(),
    )
    const quoteCall = fetchMock.mock.calls.find(([input]) =>
      String(input).endsWith('/quote'),
    )
    const quoteBody = JSON.parse(String(quoteCall?.[1]?.body)) as {
      products: unknown[]
    }
    expect(quoteBody.products).toHaveLength(2)
  })

  it('keeps a failed quote in NUEVA and shows a useful error', async () => {
    const opportunity = makeOpportunity('NUEVA')
    mockApi({
      opportunities: [opportunity],
      actionResponse: (url) =>
        url.pathname.endsWith('/quote')
          ? jsonResponse(409, { detail: 'Product is inactive' })
          : undefined,
    })
    const { container } = render(<PipelinePage />)
    await waitForPipeline()

    fireEvent.click(screen.getByRole('button', { name: 'Mover a Cotizada' }))
    fireEvent.change(await screen.findByLabelText('Producto'), {
      target: { value: '10' },
    })
    fireEvent.change(screen.getByLabelText('Cantidad (kg)'), {
      target: { value: '2500' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar cotización' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'ya no está activo',
    )
    expect(within(getStage(container, 'NUEVA')).getByText('Cliente NUEVA')).toBeInTheDocument()
  })

  it('moves COTIZADA to NEGOCIACION optimistically and confirms the API result', async () => {
    const opportunity = makeOpportunity('COTIZADA')
    mockApi({
      opportunities: [opportunity],
      actionResponse: (url) =>
        url.pathname.endsWith('/move-to-negotiation')
          ? jsonResponse(200, movedOpportunity(opportunity, 'NEGOCIACION'))
          : undefined,
    })
    const { container } = render(<PipelinePage />)
    await waitForPipeline()

    fireEvent.click(screen.getByRole('button', { name: 'Mover a Negociación' }))

    await waitFor(() =>
      expect(within(getStage(container, 'NEGOCIACION')).getByText('Cliente COTIZADA')).toBeInTheDocument(),
    )
  })

  it('moves NEGOCIACION to GANADA', async () => {
    const opportunity = makeOpportunity('NEGOCIACION')
    mockApi({
      opportunities: [opportunity],
      actionResponse: (url) =>
        url.pathname.endsWith('/win')
          ? jsonResponse(200, movedOpportunity(opportunity, 'GANADA'))
          : undefined,
    })
    const { container } = render(<PipelinePage />)
    await waitForPipeline()

    fireEvent.click(screen.getByRole('button', { name: 'Mover a Ganada' }))

    await waitFor(() =>
      expect(within(getStage(container, 'GANADA')).getByText('Cliente NEGOCIACION')).toBeInTheDocument(),
    )
  })

  it('reverts an optimistic transition when the API rejects it', async () => {
    const opportunity = makeOpportunity('COTIZADA')
    mockApi({
      opportunities: [opportunity],
      actionResponse: (url) =>
        url.pathname.endsWith('/move-to-negotiation')
          ? jsonResponse(409, { detail: 'Invalid transition' })
          : undefined,
    })
    const { container } = render(<PipelinePage />)
    await waitForPipeline()

    fireEvent.click(screen.getByRole('button', { name: 'Mover a Negociación' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'se mantuvo sin cambios',
    )
    expect(
      within(getStage(container, 'COTIZADA')).getByText('Cliente COTIZADA'),
    ).toBeInTheDocument()
  })

  it('blocks an invalid drag target without calling a transition', async () => {
    const opportunity = makeOpportunity('NUEVA')
    const fetchMock = mockApi({ opportunities: [opportunity] })
    render(<PipelinePage />)
    await waitForPipeline()
    const callsBeforeDrop = fetchMock.mock.calls.length

    simulateDrop(opportunity, 'GANADA')

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(callsBeforeDrop)
  })

  it('requires a loss reason and removes a successfully lost opportunity', async () => {
    const opportunity = makeOpportunity('NUEVA')
    const fetchMock = mockApi({
      opportunities: [opportunity],
      actionResponse: (url) =>
        url.pathname.endsWith('/lose')
          ? jsonResponse(200, movedOpportunity(opportunity, 'PERDIDA'))
          : undefined,
    })
    const { container } = render(<PipelinePage />)
    await waitForPipeline()

    fireEvent.click(screen.getByRole('button', { name: 'Marcar como perdida' }))
    const lossDialog = await screen.findByRole('dialog', {
      name: 'Marcar como perdida',
    })
    expect(within(lossDialog).getByLabelText('Motivo')).toHaveFocus()
    fireEvent.click(within(lossDialog).getByRole('button', { name: 'Confirmar pérdida' }))
    expect(await within(lossDialog).findByRole('alert')).toHaveTextContent(
      'Seleccioná un motivo',
    )

    fireEvent.change(within(lossDialog).getByLabelText('Motivo'), {
      target: { value: 'PRECIO' },
    })
    fireEvent.click(within(lossDialog).getByRole('button', { name: 'Confirmar pérdida' }))

    await waitFor(() =>
      expect(within(getStage(container, 'NUEVA')).queryByText('Cliente NUEVA')).not.toBeInTheDocument(),
    )
    const loseCall = fetchMock.mock.calls.find(([input]) =>
      String(input).endsWith('/lose'),
    )
    expect(JSON.parse(String(loseCall?.[1]?.body))).toEqual({
      loss_reason: 'PRECIO',
    })
  })

  it.each(['SUPERVISOR', 'VENDEDOR'] as const)(
    'keeps the accessible movement controls available to %s',
    async (role) => {
      authState.role = role
      mockApi({ opportunities: [makeOpportunity('COTIZADA')] })
      render(<PipelinePage />)

      expect(
        await screen.findByRole('button', { name: 'Mover a Negociación' }),
      ).toBeInTheDocument()
      expect(
        screen.getByRole('button', {
          name: /Arrastrar oportunidad de Cliente COTIZADA/,
        }),
      ).toBeInTheDocument()
    },
  )

  it('restores focus to the movement trigger when the quote dialog closes', async () => {
    mockApi({ opportunities: [makeOpportunity('NUEVA')] })
    render(<PipelinePage />)
    const moveButton = await screen.findByRole('button', {
      name: 'Mover a Cotizada',
    })
    moveButton.focus()
    fireEvent.click(moveButton)
    const dialog = await screen.findByRole('dialog', {
      name: 'Cotizar oportunidad',
    })

    fireEvent.click(within(dialog).getByRole('button', { name: 'Cancelar' }))

    await waitFor(() => expect(moveButton).toHaveFocus())
  })
})
