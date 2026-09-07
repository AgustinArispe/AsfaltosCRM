import { describe, expect, it, vi } from 'vitest'

import {
  createOpportunityNote,
  createWhatsAppOpportunity,
  getOpportunityDetail,
  listCustomerOpportunities,
  listOpportunityNotes,
  listPipelineOpportunities,
  loseOpportunity,
  moveOpportunityToNegotiation,
  quoteOpportunity,
  reopenOpportunity,
  updateOpportunityAssignee,
  updateOpportunityQuoteProducts,
  winOpportunity,
} from './opportunities'

describe('Opportunity API client', () => {
  it('keeps entity-scoped reads and mutations on their typed contracts', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL): Promise<Response> => {
      const url = new URL(String(input), 'http://localhost')
      const body =
        url.pathname === '/api/opportunities'
          ? { items: [], page: 1, page_size: 100, total: 0 }
          : {}
      return new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      })
    })
    vi.stubGlobal('fetch', fetchMock)
    const session = { token: 'token', onUnauthorized: vi.fn() }

    await listCustomerOpportunities(8, session)
    await listPipelineOpportunities(session)
    await getOpportunityDetail(9, session)
    await createWhatsAppOpportunity(8, session)
    await updateOpportunityAssignee(9, 4, '2026-09-07T12:00:00Z', session)
    await quoteOpportunity(9, [{ product_id: 1, quantity_kg: 100 }], session)
    await updateOpportunityQuoteProducts(
      9,
      [{ product_id: 1, quantity_kg: 200 }],
      '2026-09-07T12:00:00Z',
      session,
    )
    await moveOpportunityToNegotiation(9, session)
    await winOpportunity(9, session)
    await loseOpportunity(9, 'OTRO', session)
    await reopenOpportunity(9, session)
    await listOpportunityNotes(9, session)
    await createOpportunityNote(9, 'Seguimiento', session, '00000000-0000-4000-8000-000000000001')

    const paths = fetchMock.mock.calls.map(
      ([input]) => new URL(String(input), 'http://localhost').pathname,
    )
    expect(paths).toContain('/api/opportunities/9/assignee')
    expect(paths).toContain('/api/opportunities/9/lose')
    expect(paths).toContain('/api/opportunities/9/reopen')
    expect(paths.filter((path) => path === '/api/opportunities/9/notes')).toHaveLength(2)
  })
})
