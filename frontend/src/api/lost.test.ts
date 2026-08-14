import { describe, expect, it, vi } from 'vitest'
import { EMPTY_LOST_FILTERS, type LostFilters } from '../lost/types'
import { getLostStatistics, listLostOpportunities } from './lost'

const session = { token: 'lost-api-token', onUnauthorized: vi.fn() }

describe('Lost API client', () => {
  it('uses the authoritative cursor endpoint without inventing filters', async () => {
    const fetchMock = vi.fn(
      async () => new Response(JSON.stringify({ items: [], next_cursor: null }), { status: 200 }),
    )
    vi.stubGlobal('fetch', fetchMock)
    await listLostOpportunities(EMPTY_LOST_FILTERS, null, session)
    expect(fetchMock).toHaveBeenCalledWith('/api/lost-opportunities?limit=20', expect.any(Object))
  })

  it('serializes only supported server filters and half-open dates', async () => {
    const fetchMock = vi.fn(
      async (input: RequestInfo | URL) =>
        new Response(
          JSON.stringify(
            String(input).includes('statistics')
              ? { current_count: 1 }
              : { items: [], next_cursor: 'next' },
          ),
          { status: 200 },
        ),
    )
    vi.stubGlobal('fetch', fetchMock)
    const filters: LostFilters = {
      search: 'sur',
      reasons: ['PRECIO', 'OTRO'],
      customerId: 9,
      province: 'Buenos Aires',
      productId: 3,
      source: 'WEB',
      lostFrom: '2026-08-01',
      lostTo: '2026-08-15',
    }
    await listLostOpportunities(filters, 'opaque-cursor', session)
    await getLostStatistics(filters, session)
    const listUrl = String(fetchMock.mock.calls[0]?.[0])
    expect(listUrl).toContain('search=sur')
    expect(listUrl).toContain('reason=PRECIO')
    expect(listUrl).toContain('reason=OTRO')
    expect(listUrl).toContain('customer_id=9')
    expect(listUrl).toContain('lost_from=2026-08-01T00%3A00%3A00Z')
    expect(listUrl).toContain('cursor=opaque-cursor')
    expect(String(fetchMock.mock.calls[1]?.[0])).not.toContain('limit=')
  })
})
