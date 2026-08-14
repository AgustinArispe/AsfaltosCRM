import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useNotifications } from './useNotifications'

const older = {
  id: 1,
  type: 'OPPORTUNITY_STALE' as const,
  created_at: '2026-08-13T14:00:00Z',
  read_at: null,
  resolved_at: null,
  opportunity: {
    id: 1,
    status: 'NUEVA' as const,
    current_status_entered_at: '2026-07-30T14:00:00Z',
    customer: { id: 1, name: 'Anterior', company: null },
  },
}

const newer = { ...older, id: 3, created_at: '2026-08-15T14:00:00Z' }
const secondPage = { ...older, id: 2, created_at: '2026-08-14T14:00:00Z' }
const session = { token: 'token', onUnauthorized: vi.fn() }

function response(items: unknown[], total: number): Response {
  return new Response(JSON.stringify({ items, page: 1, page_size: 25, total }), {
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('notification list reconciliation', () => {
  beforeEach(() => {
    Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'visible' })
    Object.defineProperty(navigator, 'onLine', { configurable: true, value: true })
    Object.defineProperty(window, 'scrollY', { configurable: true, value: 0 })
  })

  afterEach(() => {
    Object.defineProperty(window, 'scrollY', { configurable: true, value: 0 })
  })

  it('loads more with stable ID de-duplication and preserves newest-first order', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(response([older], 2))
      .mockResolvedValueOnce(response([secondPage], 2))
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useNotifications('all', session))
    await waitFor(() => expect(result.current.items).toHaveLength(1))
    act(() => result.current.loadMore())
    await waitFor(() => expect(result.current.items).toHaveLength(2))
    expect(result.current.items.map((item) => item.id)).toEqual([2, 1])
    expect(new URL(String(fetchMock.mock.calls[1]?.[0]), 'http://localhost').search).toContain(
      'page=2',
    )
  })

  it('holds refreshed first-page rows while the reader has scrolled away, then applies them', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(response([older], 1))
      .mockResolvedValueOnce(response([newer], 2))
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useNotifications('all', session))
    await waitFor(() => expect(result.current.items).toHaveLength(1))
    Object.defineProperty(window, 'scrollY', { configurable: true, value: 40 })
    act(() => window.dispatchEvent(new Event('focus')))
    await waitFor(() => expect(result.current.pendingFirstPage).not.toBeNull())
    expect(result.current.items.map((item) => item.id)).toEqual([1])
    act(() => result.current.applyPendingFirstPage())
    expect(result.current.items.map((item) => item.id)).toEqual([3, 1])
  })

  it('retains loaded rows and exposes a scoped background error after a refresh failure', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(response([older], 1))
        .mockRejectedValueOnce(new Error('offline')),
    )
    const { result } = renderHook(() => useNotifications('all', session))
    await waitFor(() => expect(result.current.items).toHaveLength(1))
    act(() => window.dispatchEvent(new Event('focus')))
    await waitFor(() => expect(result.current.error).toBe('background'))
    expect(result.current.items.map((item) => item.id)).toEqual([1])
  })
})
