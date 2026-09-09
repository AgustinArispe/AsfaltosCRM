import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { DashboardPage } from './DashboardPage'

const authState = vi.hoisted(() => ({ logout: vi.fn() }))

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({ token: 'dashboard-token', logout: authState.logout }),
}))

type MockOptions = {
  delay?: boolean
  manyProvinces?: boolean
  nullConversion?: boolean
  timelineFailure?: boolean
}

function response(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    headers: { 'Content-Type': 'application/json' },
    status,
  })
}

const period = { from: '2026-08-01T03:00:00Z', to: '2026-09-01T03:00:00Z' }

function mockDashboardApi(options: MockOptions = {}) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL): Promise<Response> => {
    if (options.delay) await new Promise((resolve) => window.setTimeout(resolve, 20))
    const url = new URL(String(input), 'http://localhost')
    if (url.pathname === '/api/products') {
      return response([
        { id: 1, name: 'Asfalto base', is_active: true },
        { id: 2, name: 'Producto histórico', is_active: false },
      ])
    }
    if (url.pathname === '/api/metrics/overview') {
      return response({
        period,
        opportunities: {
          created: 9,
          won: options.nullConversion ? 0 : 4,
          lost: options.nullConversion ? 0 : 2,
          open: 3,
          conversion_rate: options.nullConversion ? null : '0.6667',
        },
        volume_kg: {
          quoted: '2500.125',
          won: options.nullConversion ? '0.000' : '1200.000',
          lost: options.nullConversion ? '0.000' : '600.000',
          open: '700.125',
          conversion_rate: options.nullConversion ? null : '0.6667',
        },
      })
    }
    if (url.pathname === '/api/metrics/timeline') {
      if (options.timelineFailure) return response({ detail: 'timeline failed' }, 500)
      return response({
        period,
        granularity: url.searchParams.get('granularity') ?? 'day',
        timezone: 'America/Argentina/Buenos_Aires',
        items: [
          {
            bucket: '2026-08-01',
            leads_created: 2,
            won: 1,
            lost: 0,
            kg_won: '100.000',
            kg_lost: '0.000',
          },
          {
            bucket: '2026-08-02',
            leads_created: 3,
            won: 0,
            lost: 1,
            kg_won: '0.000',
            kg_lost: '50.000',
          },
        ],
      })
    }
    if (url.pathname === '/api/metrics/timeline/day-opportunities') {
      return response({
        bucket: url.searchParams.get('bucket'),
        series: url.searchParams.get('series'),
        timezone: 'America/Argentina/Buenos_Aires',
        page: 1,
        page_size: 20,
        total: 1,
        items: [
          {
            opportunity_id: 41,
            customer_name: 'Hormigones Sur',
            customer_company: 'HS SA',
            current_status: 'COTIZADA',
            source: 'WEB',
            products: [
              {
                product_id: 1,
                product_name: 'Asfalto base',
                quantity_kg: '750.000',
                is_active: true,
              },
            ],
          },
        ],
      })
    }
    if (url.pathname === '/api/metrics/pipeline') {
      return response({
        snapshot_at: '2026-08-14T14:00:00Z',
        items: [
          { status: 'NUEVA', count: 3 },
          { status: 'COTIZADA', count: 2 },
          { status: 'NEGOCIACION', count: 1 },
          { status: 'GANADA', count: 4 },
          { status: 'PERDIDA', count: 2 },
        ],
      })
    }
    if (url.pathname === '/api/metrics/products') {
      return response({
        period,
        items: [
          {
            product_id: 1,
            product_name: 'Asfalto base',
            opportunities_quoted: 4,
            kg_quoted: '2000.000',
            opportunities_won: 2,
            kg_won: '1000.000',
            opportunities_lost: 1,
            kg_lost: '500.000',
            conversion_rate_opportunities: '0.6667',
            conversion_rate_kg: '0.6667',
          },
          {
            product_id: 2,
            product_name: 'Producto histórico',
            opportunities_quoted: 1,
            kg_quoted: '500.125',
            opportunities_won: 0,
            kg_won: '0.000',
            opportunities_lost: 1,
            kg_lost: '50.000',
            conversion_rate_opportunities: '0.0000',
            conversion_rate_kg: '0.0000',
          },
        ],
      })
    }
    if (url.pathname === '/api/metrics/sources') {
      return response({
        period,
        items: [
          { source: 'WEB', created: 6, won: 3, lost: 1, conversion_rate: '0.7500' },
          { source: 'WHATSAPP', created: 3, won: 1, lost: 1, conversion_rate: '0.5000' },
        ],
      })
    }
    if (url.pathname === '/api/metrics/provinces') {
      return response({
        period,
        items: [
          {
            province: 'Buenos Aires',
            opportunities_created: 3,
            opportunities_won: 2,
            opportunities_lost: 0,
            conversion_rate: '1.0000',
            kg_quoted: '1000.000',
            kg_won: '800.000',
            kg_lost: '0.000',
          },
          {
            province: null,
            opportunities_created: 5,
            opportunities_won: 1,
            opportunities_lost: 2,
            conversion_rate: '0.3333',
            kg_quoted: '1200.000',
            kg_won: '400.000',
            kg_lost: '600.000',
          },
          ...(options.manyProvinces
            ? ['Córdoba', 'Santa Fe', 'Mendoza', 'Neuquén', 'Río Negro'].map((province, index) => ({
                province,
                opportunities_created: 4 - Math.min(index, 3),
                opportunities_won: 1,
                opportunities_lost: 1,
                conversion_rate: '0.5000',
                kg_quoted: `${900 - index * 100}.000`,
                kg_won: '300.000',
                kg_lost: '200.000',
              }))
            : []),
        ],
      })
    }
    if (url.pathname === '/api/notifications') {
      return response({
        items: [],
        page: 1,
        page_size: 1,
        total: url.searchParams.get('unread_only') === 'true' ? 1 : 2,
      })
    }
    if (url.pathname === '/api/whatsapp/conversations/attention-summary') {
      return response({ waiting_count: 3, oldest_waiting_since_at: '2026-08-14T12:00:00Z' })
    }
    throw new Error(`Unexpected request ${url.pathname}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

async function renderLoaded(options: MockOptions = {}) {
  const fetchMock = mockDashboardApi(options)
  render(<DashboardPage />)
  await screen.findByRole('heading', { name: 'Necesita atención' })
  return fetchMock
}

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    vi.setSystemTime(new Date('2026-08-14T15:00:00Z'))
    authState.logout.mockReset()
  })

  afterEach(() => {
    window.history.replaceState(null, '', '/dashboard')
  })

  it('renders the approved attention, result, active, evolution and distribution hierarchy', async () => {
    await renderLoaded()

    expect(screen.getByText('oportunidades sin seguimiento')).toBeInTheDocument()
    expect(screen.getByText('conversaciones pendientes de respuesta')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Resultado del período' })).toBeInTheDocument()
    expect(screen.getByText('1.200 kg')).toBeInTheDocument()
    expect(screen.getByText('600 kg')).toBeInTheDocument()
    expect(screen.getByText('1–31 agosto 2026')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ver ganadas' })).toHaveAttribute(
      'href',
      '/won?period=month&from=2026-08-01&to=2026-08-31',
    )
    expect(screen.queryByRole('link', { name: 'Ver pérdidas' })).not.toBeInTheDocument()
    const activeSection = screen
      .getByRole('heading', { name: 'Oportunidades activas ahora' })
      .closest('section')
    if (!activeSection) throw new Error('Active Opportunities section is missing')
    expect(within(activeSection).getByText('6')).toBeInTheDocument()
    expect(within(activeSection).getByText('Nueva')).toBeInTheDocument()
    expect(within(activeSection).getByText('Cotizada')).toBeInTheDocument()
    expect(within(activeSection).getByText('Negociación')).toBeInTheDocument()
    expect(within(activeSection).queryByText(/Snapshot/i)).not.toBeInTheDocument()
    expect(
      activeSection.querySelector('.dashboard-pipeline-bar__segment--cotizada'),
    ).toBeInTheDocument()
    expect(screen.queryByText('Kg cotizados')).not.toBeInTheDocument()
    expect(screen.getAllByRole('img', { name: /Creadas|Ganadas|Pérdidas/ }).length).toBeGreaterThan(
      0,
    )

    fireEvent.click(screen.getByText('Ver datos exactos de evolución'))
    expect(screen.getAllByRole('table')[0]).toHaveTextContent('Creadas')
    expect(screen.getByText('Producto histórico')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Provincias' }))
    expect(screen.getByText('Sin provincia')).toBeInTheDocument()
  })

  it('uses typed navigation for every operational attention action', async () => {
    await renderLoaded()
    fireEvent.click(screen.getByRole('link', { name: /Ver seguimientos/ }))
    expect(window.location.pathname).toBe('/notifications')
    expect(window.location.search).toBe('?view=active')
    window.history.replaceState(null, '', '/dashboard')
    fireEvent.click(screen.getByRole('link', { name: /Abrir pendientes/ }))
    expect(window.location.pathname).toBe('/whatsapp')
    expect(window.location.search).toBe('?waiting=true')
  })

  it('applies compact filters, keeps Pipeline date-unfiltered, and resets them', async () => {
    const fetchMock = await renderLoaded()
    fireEvent.change(screen.getByLabelText('Origen', { selector: 'select' }), {
      target: { value: 'WHATSAPP' },
    })
    await waitFor(() => expect(fetchMock.mock.calls.length).toBeGreaterThan(10))
    const latestPipeline = [...fetchMock.mock.calls]
      .map(([input]) => new URL(String(input), 'http://localhost'))
      .reverse()
      .find((url) => url.pathname === '/api/metrics/pipeline')
    expect(latestPipeline?.searchParams.get('source')).toBe('WHATSAPP')
    expect(latestPipeline?.searchParams.has('from')).toBe(false)

    fireEvent.click(screen.getByText(/Filtros/))
    fireEvent.change(screen.getByLabelText('Producto'), { target: { value: '2' } })
    fireEvent.change(screen.getByLabelText('Provincia'), { target: { value: 'Buenos Aires' } })
    expect(await screen.findByRole('button', { name: 'Restablecer' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Restablecer' }))
    expect(screen.getByLabelText('Origen', { selector: 'select' })).toHaveValue('')
    expect(screen.getByLabelText('Producto')).toHaveValue('')
  })

  it('refetches only resources that depend on changed commercial filters', async () => {
    const fetchMock = await renderLoaded()
    const counts = () => {
      const paths = fetchMock.mock.calls.map(
        ([input]) => new URL(String(input), 'http://localhost').pathname,
      )
      return {
        commercial: paths.filter(
          (path) => path.startsWith('/api/metrics/') && path !== '/api/metrics/pipeline',
        ).length,
        pipeline: paths.filter((path) => path === '/api/metrics/pipeline').length,
        notifications: paths.filter((path) => path === '/api/notifications').length,
        waiting: paths.filter((path) => path === '/api/whatsapp/conversations/attention-summary')
          .length,
        catalog: paths.filter((path) => path === '/api/products').length,
      }
    }
    const initial = counts()
    fireEvent.change(screen.getByLabelText('Período'), { target: { value: 'last-three-months' } })
    await waitFor(() => expect(counts().commercial).toBe(initial.commercial + 5))
    expect(counts()).toEqual({
      commercial: initial.commercial + 5,
      pipeline: initial.pipeline,
      notifications: initial.notifications,
      waiting: initial.waiting,
      catalog: initial.catalog,
    })

    const beforeDimension = counts()
    fireEvent.change(screen.getByLabelText('Origen', { selector: 'select' }), {
      target: { value: 'WHATSAPP' },
    })
    await waitFor(() => expect(counts().commercial).toBe(beforeDimension.commercial + 5))
    expect(counts()).toEqual({
      commercial: beforeDimension.commercial + 5,
      pipeline: beforeDimension.pipeline + 1,
      notifications: beforeDimension.notifications,
      waiting: beforeDimension.waiting,
      catalog: beforeDimension.catalog,
    })
  })

  it('supports custom dates and changes long periods to monthly timeline buckets', async () => {
    const fetchMock = await renderLoaded()
    fireEvent.change(screen.getByLabelText('Período'), { target: { value: 'custom' } })
    fireEvent.change(screen.getByLabelText('Desde'), { target: { value: '2024-01-01' } })
    fireEvent.change(screen.getByLabelText('Hasta'), { target: { value: '2026-08-14' } })
    await waitFor(() => {
      const timeline = [...fetchMock.mock.calls]
        .map(([input]) => new URL(String(input), 'http://localhost'))
        .reverse()
        .find((url) => url.pathname === '/api/metrics/timeline')
      expect(timeline?.searchParams.get('granularity')).toBe('month')
      expect(timeline?.searchParams.get('to')).toBe('2026-08-15T00:00:00-03:00')
    })
  })

  it('states null conversion honestly without drawing a misleading ring', async () => {
    await renderLoaded({ nullConversion: true })
    expect(screen.getByText('Sin resultados cerrados en el período')).toBeInTheDocument()
    expect(screen.getByText('Sin volumen cerrado en el período')).toBeInTheDocument()
  })

  it('keeps other surfaces visible when an independent chart request fails and supports loading skeletons', async () => {
    mockDashboardApi({ delay: true, timelineFailure: true })
    render(<DashboardPage />)
    expect(screen.getByRole('status', { name: 'Cargando Dashboard' })).toBeInTheDocument()
    expect(
      await screen.findByText(
        'No pudimos actualizar esta información. Conservamos los últimos datos disponibles.',
      ),
    ).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Resultado del período' })).toBeInTheDocument()
  })

  it('keeps table and chart controls keyboard-accessible', async () => {
    await renderLoaded()
    fireEvent.change(screen.getByLabelText('Período'), { target: { value: 'custom' } })
    fireEvent.change(screen.getByLabelText('Desde'), { target: { value: '2026-08-01' } })
    fireEvent.change(screen.getByLabelText('Hasta'), { target: { value: '2026-08-10' } })
    const createdBar = await screen.findByRole('button', { name: /Creadas 3, abrir oportunidades/ })
    fireEvent.click(createdBar)
    expect(
      await screen.findByRole('region', { name: 'Oportunidades del día seleccionado' }),
    ).toHaveTextContent('Hormigones Sur')
    expect(screen.getByRole('link', { name: 'Hormigones Sur' })).toHaveAttribute(
      'href',
      '/pipeline/opportunities/41',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Cerrar detalle del día' }))
    expect(
      screen.queryByRole('region', { name: 'Oportunidades del día seleccionado' }),
    ).not.toBeInTheDocument()
  })

  it('preserves every province in the compact secondary analysis', async () => {
    await renderLoaded({ manyProvinces: true })
    fireEvent.click(screen.getByRole('button', { name: 'Provincias' }))
    expect(screen.getByRole('list', { name: /Sin provincia: 5.*Mendoza: 2/ })).toBeInTheDocument()
  })

  it('keeps Origin visible and switches only the secondary dimension', async () => {
    await renderLoaded()
    expect(screen.getByRole('button', { name: 'Productos' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(screen.getByRole('list', { name: /Web: 6.*WhatsApp: 3/ })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Provincias' }))
    expect(screen.getByRole('button', { name: 'Provincias' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })
})
