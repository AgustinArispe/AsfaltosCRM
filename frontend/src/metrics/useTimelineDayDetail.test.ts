import { act, renderHook, waitFor } from '@testing-library/react'
import { expect, it, vi } from 'vitest'

import type { MetricsFilters, TimelineDayOpportunity } from './types'
import { useTimelineDayDetail } from './useTimelineDayDetail'

const filters: MetricsFilters = {
  from: '2026-09-01T00:00:00-03:00',
  to: '2026-10-01T00:00:00-03:00',
  source: null,
  productId: null,
  province: null,
}

const item: TimelineDayOpportunity = {
  opportunity_id: 7,
  loss_event_id: null,
  customer_name: 'Cliente referido',
  customer_company: null,
  current_status: 'NUEVA',
  source: 'REFERIDO',
  products: [],
}

function response(page: number) {
  return new Response(
    JSON.stringify({
      bucket: '2026-09-10',
      series: 'created',
      timezone: 'America/Argentina/Buenos_Aires',
      page,
      page_size: 1,
      total: 2,
      items: [{ ...item, opportunity_id: page === 1 ? 7 : 8 }],
    }),
    { status: 200, headers: { 'Content-Type': 'application/json' } },
  )
}

it('opens, paginates, resets with filters and closes daily detail', async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input), 'http://localhost')
    return response(Number(url.searchParams.get('page')))
  })
  vi.stubGlobal('fetch', fetchMock)
  const session = { token: 'token', onUnauthorized: vi.fn() }
  const { result, rerender } = renderHook(
    ({ activeFilters }) => useTimelineDayDetail(activeFilters, session),
    { initialProps: { activeFilters: filters } },
  )

  act(() => result.current.open('2026-09-10', 'created'))
  act(() => result.current.open('2026-09-10', 'created'))
  await waitFor(() => expect(result.current.items).toHaveLength(1))
  expect(fetchMock).toHaveBeenCalledTimes(1)

  act(() => result.current.loadMore())
  await waitFor(() => expect(result.current.items).toHaveLength(2))
  expect(result.current.total).toBe(2)

  rerender({ activeFilters: { ...filters, source: 'REFERIDO' } })
  await waitFor(() => expect(result.current.selected).toBeNull())
  act(() => result.current.close())
  expect(result.current.items).toEqual([])
})

it('exposes a recoverable daily-detail error', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Sin conexión')))
  const { result } = renderHook(() =>
    useTimelineDayDetail(filters, { token: 'token', onUnauthorized: vi.fn() }),
  )

  act(() => result.current.open('2026-09-10', 'won'))
  await waitFor(() => expect(result.current.error).toBe('Sin conexión'))
  expect(result.current.isLoading).toBe(false)
})
