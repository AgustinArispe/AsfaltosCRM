import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { expect, it, vi } from 'vitest'

import { MetricDrilldown } from './MetricDrilldown'
import type { MetricsFilters } from './types'

const filters: MetricsFilters = {
  from: '2026-09-01T00:00:00-03:00',
  to: '2026-10-01T00:00:00-03:00',
  source: null,
  productId: null,
  province: null,
}

it('paginates a bounded opportunity drilldown in both directions', async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input), 'http://localhost')
    const page = Number(url.searchParams.get('page'))
    return new Response(
      JSON.stringify({
        page,
        page_size: 1,
        total: 2,
        items: [
          {
            opportunity_id: page,
            loss_event_id: null,
            customer_name: `Cliente ${page}`,
            customer_company: null,
            current_status: 'NUEVA',
            source: 'REFERIDO',
            relevant_at: '2026-09-10T12:00:00Z',
            quantity_kg: '0.000',
            loss_reason: null,
          },
        ],
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } },
    )
  })
  vi.stubGlobal('fetch', fetchMock)

  render(
    <MetricDrilldown
      filters={filters}
      onClose={vi.fn()}
      selection={{ title: 'Oportunidades creadas', kind: 'created' }}
      session={{ token: 'token', onUnauthorized: vi.fn() }}
    />,
  )

  await screen.findByRole('button', { name: 'Abrir oportunidad 1 de Cliente 1' })
  fireEvent.click(screen.getByRole('button', { name: 'Página siguiente' }))
  await screen.findByRole('button', { name: 'Abrir oportunidad 2 de Cliente 2' })
  fireEvent.click(screen.getByRole('button', { name: 'Página anterior' }))
  await waitFor(() =>
    expect(
      screen.getByRole('button', { name: 'Abrir oportunidad 1 de Cliente 1' }),
    ).toBeInTheDocument(),
  )
  expect(fetchMock).toHaveBeenCalledTimes(3)
})
