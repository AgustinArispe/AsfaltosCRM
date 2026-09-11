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
  zeroPipeline?: boolean
  zeroTimeline?: boolean
  timelineFailure?: boolean
  twoStagePipeline?: boolean
}

function response(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    headers: { 'Content-Type': 'application/json' },
    status,
  })
}

const period = { from: '2026-08-01T03:00:00Z', to: '2026-09-01T03:00:00Z' }

function dailyTimelineItems(from: string, to: string, zeroTimeline: boolean) {
  const items = []
  const cursor = new Date(`${from.slice(0, 10)}T12:00:00Z`)
  const end = new Date(`${to.slice(0, 10)}T12:00:00Z`)
  let index = 0
  while (cursor < end) {
    items.push({
      bucket: cursor.toISOString().slice(0, 10),
      leads_created: zeroTimeline ? 0 : index === 0 ? 2 : index === 1 ? 3 : 0,
      won: zeroTimeline ? 0 : index === 0 ? 1 : 0,
      lost: zeroTimeline ? 0 : index === 1 ? 1 : 0,
      kg_won: index === 0 ? '100.000' : '0.000',
      kg_lost: index === 1 ? '50.000' : '0.000',
    })
    cursor.setUTCDate(cursor.getUTCDate() + 1)
    index += 1
  }
  return items
}

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
      const from = url.searchParams.get('from') ?? period.from
      const to = url.searchParams.get('to') ?? period.to
      const granularity = url.searchParams.get('granularity') ?? 'day'
      return response({
        period,
        granularity,
        timezone: 'America/Argentina/Buenos_Aires',
        items:
          granularity === 'day'
            ? dailyTimelineItems(from, to, Boolean(options.zeroTimeline))
            : dailyTimelineItems('2026-08-01', '2026-08-03', Boolean(options.zeroTimeline)),
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
    if (url.pathname === '/api/metrics/opportunities') {
      return response({
        page: 1,
        page_size: 20,
        total: 1,
        items: [
          {
            opportunity_id: 41,
            loss_event_id: null,
            customer_name: 'Hormigones Sur',
            customer_company: 'HS SA',
            current_status: 'COTIZADA',
            source: 'WEB',
            relevant_at: '2026-08-14T12:00:00Z',
            quantity_kg: '750.000',
            loss_reason: null,
          },
        ],
      })
    }
    if (url.pathname === '/api/metrics/pipeline') {
      return response({
        snapshot_at: '2026-08-14T14:00:00Z',
        items: [
          { status: 'NUEVA', count: options.zeroPipeline ? 0 : options.twoStagePipeline ? 8 : 9 },
          {
            status: 'COTIZADA',
            count: options.zeroPipeline ? 0 : options.twoStagePipeline ? 2 : 4,
          },
          {
            status: 'NEGOCIACION',
            count: options.zeroPipeline || options.twoStagePipeline ? 0 : 5,
          },
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
  await screen.findByRole('heading', { name: 'Resultado del período' })
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

  it('renders the approved result, active, evolution and distribution hierarchy without attention', async () => {
    await renderLoaded()

    expect(screen.queryByRole('heading', { name: 'Resumen comercial' })).not.toBeInTheDocument()
    expect(screen.queryByText('Necesita atención')).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Resultado del período' })).toBeInTheDocument()
    expect(screen.getByText('1.200 kg')).toBeInTheDocument()
    expect(screen.getByText('600 kg')).toBeInTheDocument()
    expect(screen.getByText('1–31 agosto 2026')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Ganadas4 ganadas/ })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Ver pérdidas' })).not.toBeInTheDocument()
    const activeSection = screen
      .getByRole('heading', { name: 'Oportunidades activas' })
      .closest('section')
    if (!activeSection) throw new Error('Active Opportunities section is missing')
    expect(within(activeSection).getByText('18')).toBeInTheDocument()
    expect(within(activeSection).getByText('Nueva')).toBeInTheDocument()
    expect(within(activeSection).getByText('Cotizada')).toBeInTheDocument()
    expect(within(activeSection).getByText('Negociación')).toBeInTheDocument()
    expect(within(activeSection).queryByText(/Snapshot/i)).not.toBeInTheDocument()
    expect(activeSection.querySelector('.dashboard-pipeline-bar')).not.toBeInTheDocument()
    expect(
      within(activeSection).getByRole('button', { name: /etapa Cotizada/i }),
    ).toBeInTheDocument()
    expect(screen.queryByText('Kg cotizados')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Evolución comercial diaria')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /Abrir movimientos de/ })).toHaveLength(31)
    const dailyChart = screen.getByLabelText('Evolución comercial diaria')
    expect(dailyChart.querySelectorAll('[data-bucket="2026-08-01"]')).toHaveLength(2)
    expect(dailyChart.querySelectorAll('[data-bucket="2026-08-03"]')).toHaveLength(0)

    fireEvent.click(screen.getByText('Ver datos exactos de evolución'))
    expect(screen.getAllByRole('table')[0]).toHaveTextContent('Creadas')
    expect(screen.getAllByText('Producto histórico').length).toBeGreaterThan(0)
    expect(screen.getByRole('heading', { name: 'Provincias' })).toBeInTheDocument()
    expect(screen.getByText('Sin provincia')).toBeInTheDocument()
  })

  it('loads metric drilldown only when an interactive metric is opened', async () => {
    const fetchMock = await renderLoaded()
    expect(
      fetchMock.mock.calls.some(([input]) => String(input).includes('/metrics/opportunities')),
    ).toBe(false)

    fireEvent.click(screen.getByRole('button', { name: /Cotizada: 4, 22 %; abrir detalle/i }))

    expect(await screen.findByRole('dialog')).toHaveAccessibleName('Oportunidades cotizadas')
    expect(await screen.findByText('Hormigones Sur')).toBeVisible()
    const opportunityCard = screen.getByRole('button', {
      name: 'Abrir oportunidad 41 de Hormigones Sur',
    })
    expect(opportunityCard).toHaveClass(
      'metric-drilldown__card',
      'opportunity-stage-tone',
      'opportunity-stage-tone--cotizada',
    )
    expect(opportunityCard.querySelector('.metric-drilldown__icon')).toBeInTheDocument()
    expect(screen.getByText('750 kg')).toBeInTheDocument()
    expect(
      fetchMock.mock.calls.some(([input]) => {
        const url = new URL(String(input), 'http://localhost')
        return (
          url.pathname === '/api/metrics/opportunities' &&
          url.searchParams.get('status') === 'COTIZADA'
        )
      }),
    ).toBe(true)

    fireEvent.click(opportunityCard)
    expect(window.location.pathname).toBe('/pipeline/opportunities/41')
  })

  it('draws all active stages proportionally and links donut and legend hover states', async () => {
    await renderLoaded()
    const donut = screen.getByLabelText('Distribución de oportunidades activas por etapa')
    const nueva = within(donut).getByRole('button', { name: /Nueva: 9, 50 %/ })
    const cotizada = within(donut).getByRole('button', { name: /Cotizada: 4, 22 %/ })
    const negociacion = within(donut).getByRole('button', { name: /Negociación: 5, 28 %/ })
    const segmentLengths = [nueva, cotizada, negociacion].map(
      (segment) => Number(segment.getAttribute('data-share')) * 100,
    )

    expect(segmentLengths[0]).toBeCloseTo(50, 3)
    expect(segmentLengths[1]).toBeCloseTo(22.222, 3)
    expect(segmentLengths[2]).toBeCloseTo(27.778, 3)
    expect(donut.querySelector('[stroke-dasharray]')).not.toBeInTheDocument()
    expect(donut.querySelector('[class*="ganada"]')).not.toBeInTheDocument()

    const quotedRow = screen.getByRole('button', { name: /etapa Cotizada/i })
    fireEvent.mouseEnter(cotizada)
    expect(quotedRow).toHaveClass('is-highlighted')
    fireEvent.mouseLeave(cotizada)
    fireEvent.mouseEnter(quotedRow)
    expect(cotizada).toHaveClass('is-highlighted')
  })

  it('shows a neutral zero-active donut and keeps the total action available', async () => {
    await renderLoaded({ zeroPipeline: true })
    const donut = screen.getByLabelText('Distribución de oportunidades activas por etapa')

    expect(within(donut).queryAllByRole('button')).toHaveLength(0)
    expect(
      screen.getByRole('button', { name: 'Ver las 0 oportunidades activas' }),
    ).toHaveTextContent('0activas')
  })

  it('renders two stages as one continuous 80/20 ring without repeated color patterns', async () => {
    await renderLoaded({ twoStagePipeline: true })
    const donut = screen.getByLabelText('Distribución de oportunidades activas por etapa')
    const segments = within(donut).getAllByRole('button')

    expect(segments).toHaveLength(2)
    expect(Number(segments[0]?.getAttribute('data-share')) * 100).toBeCloseTo(80, 3)
    expect(Number(segments[1]?.getAttribute('data-share')) * 100).toBeCloseTo(20, 3)
    expect(donut.querySelector('[stroke-dasharray]')).not.toBeInTheDocument()
  })

  it('shows aligned values in the commercial evolution tooltip', async () => {
    await renderLoaded()
    const createdPoint = screen.getByRole('button', { name: /Abrir movimientos de 1 de agosto:/ })

    fireEvent.mouseEnter(createdPoint)

    const tooltip = screen.getByRole('tooltip')
    expect(tooltip).toHaveTextContent('1 de agosto')
    expect(tooltip).toHaveTextContent('Creadas2')
    expect(tooltip).toHaveTextContent('Ganadas1')
    expect(tooltip).toHaveTextContent('Pérdidas0')
  })

  it('closes the opportunity modal and restores focus to its trigger', async () => {
    await renderLoaded()
    const trigger = screen.getByRole('button', { name: /Ver oportunidades en etapa Cotizada/i })
    trigger.focus()
    fireEvent.click(trigger)
    const dialog = await screen.findByRole('dialog')

    fireEvent.click(within(dialog).getByRole('button', { name: /Cerrar oportunidades cotizadas/i }))

    await waitFor(() => expect(trigger).toHaveFocus())
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

  it('renders leap-year February with 29 clickable calendar days', async () => {
    window.history.replaceState(null, '', '/dashboard?period=custom&from=2024-02-01&to=2024-02-29')
    const fetchMock = await renderLoaded()

    expect(screen.getAllByRole('button', { name: /Abrir movimientos de/ })).toHaveLength(29)
    const timeline = fetchMock.mock.calls
      .map(([input]) => new URL(String(input), 'http://localhost'))
      .find((url) => url.pathname === '/api/metrics/timeline')
    expect(timeline?.searchParams.get('granularity')).toBe('day')
  })

  it.each([
    ['2025-02-01', '2025-02-28', 28],
    ['2026-09-01', '2026-09-30', 30],
  ])('renders the calendar range from %s through %s', async (from, to, expectedDays) => {
    window.history.replaceState(null, '', `/dashboard?period=custom&from=${from}&to=${to}`)
    await renderLoaded()

    expect(screen.getAllByRole('button', { name: /Abrir movimientos de/ })).toHaveLength(
      expectedDays,
    )
  })

  it('keeps the bounded monthly fallback for custom periods longer than one year', async () => {
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

  it('opens a bucket, then an exact daily movement in the same modal', async () => {
    const fetchMock = await renderLoaded()
    fireEvent.click(screen.getByRole('button', { name: /Abrir movimientos de 1 de agosto:/ }))

    const dialog = await screen.findByRole('dialog', { name: 'Movimientos · 1 de agosto' })
    const movement = await within(dialog).findByRole('button', { name: /2 creadas/i })
    fireEvent.click(movement)

    expect(await within(dialog).findByRole('heading', { name: 'Creadas · 1 agosto' })).toBeVisible()
    expect(
      within(dialog).getByRole('button', { name: 'Abrir oportunidad 41 de Hormigones Sur' }),
    ).toBeInTheDocument()
    expect(
      fetchMock.mock.calls.some(([input]) => {
        const url = new URL(String(input), 'http://localhost')
        return (
          url.pathname === '/api/metrics/timeline/day-opportunities' &&
          url.searchParams.get('bucket') === '2026-08-01' &&
          url.searchParams.get('series') === 'created'
        )
      }),
    ).toBe(true)
    expect(within(dialog).getByRole('button', { name: 'Volver a movimientos' })).toHaveFocus()
  })

  it('shows a compact empty Evolution state when every movement is zero', async () => {
    await renderLoaded({ zeroTimeline: true })
    expect(screen.getByText('No hay evolución en el período')).toBeInTheDocument()
    expect(screen.queryByLabelText('Evolución comercial diaria')).not.toBeInTheDocument()
  })

  it('shows the five highest-ranked provinces in an interactive donut', async () => {
    const fetchMock = await renderLoaded({ manyProvinces: true })
    const donut = screen.getByLabelText('Distribución de oportunidades creadas por provincia')
    const legend = screen.getByRole('list', {
      name: 'Detalle de oportunidades creadas por provincia',
    })

    const shares = [...donut.querySelectorAll('[data-share]')].map((segment) =>
      Number(segment.getAttribute('data-share')),
    )
    expect(shares).toHaveLength(5)
    expect(shares.reduce((sum, share) => sum + share, 0)).toBeCloseTo(1, 5)
    expect(within(legend).getByText('Sin provincia')).toBeInTheDocument()
    expect(within(legend).getByText('Mendoza')).toBeInTheDocument()
    expect(within(legend).queryByText('Río Negro')).not.toBeInTheDocument()
    expect(
      within(legend).getByRole('button', { name: 'Ver oportunidades de Córdoba' }),
    ).toBeInTheDocument()

    fireEvent.click(within(legend).getByRole('button', { name: 'Ver oportunidades de Córdoba' }))
    expect(await screen.findByRole('dialog')).toHaveAccessibleName('Oportunidades de Córdoba')
    expect(
      fetchMock.mock.calls.some(([input]) => {
        const url = new URL(String(input), 'http://localhost')
        return (
          url.pathname === '/api/metrics/opportunities' &&
          url.searchParams.get('province') === 'Córdoba'
        )
      }),
    ).toBe(true)
  })

  it('places losses beside Origin and Products, with Provinces spanning the next row', async () => {
    await renderLoaded()
    const origin = screen.getByRole('heading', { name: 'Origen de oportunidades' })
    const layout = origin.closest('.dashboard-lower-analytics')
    if (!layout) throw new Error('Lower Dashboard analytics layout is missing')

    expect([...layout.querySelectorAll('h2')].map((heading) => heading.textContent)).toEqual([
      'Origen de oportunidades',
      'Productos',
      'Pérdidas del período',
      'Provincias',
    ])
    expect(
      screen.getByRole('heading', { name: 'Pérdidas del período' }).closest('section'),
    ).toHaveClass('dashboard-losses')
    expect(screen.getByRole('heading', { name: 'Provincias' }).closest('section')).toHaveClass(
      'dashboard-provinces-wide',
    )
    expect(screen.getByRole('list', { name: /Web: 6.*WhatsApp: 3/ })).toBeInTheDocument()
  })
})
