import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { NOTIFICATION_REFRESH_INTERVAL_MS, useNotificationAttention } from './NotificationAttention'

function response(total: number): Response {
  return new Response(JSON.stringify({ items: [], page: 1, page_size: 1, total }), {
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('notification attention polling', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'visible' })
    Object.defineProperty(navigator, 'onLine', { configurable: true, value: true })
  })

  afterEach(() => vi.useRealTimers())

  it('uses the exact active-unread query every 60 seconds only while visible and online', async () => {
    let activeUnreadTotal = 4
    const fetchMock = vi.fn((_input: RequestInfo | URL) =>
      Promise.resolve(response(activeUnreadTotal)),
    )
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() =>
      useNotificationAttention({ token: 'token', onUnauthorized: vi.fn() }),
    )
    await waitFor(() => expect(result.current.count).toBe(4))
    expect(new URL(String(fetchMock.mock.calls[0]?.[0]), 'http://localhost').search).toContain(
      'unread_only=true',
    )
    const initialRequestCount = fetchMock.mock.calls.length

    await act(async () => {
      vi.advanceTimersByTime(NOTIFICATION_REFRESH_INTERVAL_MS)
    })
    expect(fetchMock).toHaveBeenCalledTimes(initialRequestCount + 1)

    Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'hidden' })
    await act(async () => {
      vi.advanceTimersByTime(NOTIFICATION_REFRESH_INTERVAL_MS)
    })
    expect(fetchMock).toHaveBeenCalledTimes(initialRequestCount + 1)

    Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'visible' })
    Object.defineProperty(navigator, 'onLine', { configurable: true, value: false })
    window.dispatchEvent(new Event('online'))
    expect(fetchMock).toHaveBeenCalledTimes(initialRequestCount + 1)

    Object.defineProperty(navigator, 'onLine', { configurable: true, value: true })
    activeUnreadTotal = 3
    window.dispatchEvent(new Event('faa-notification-attention-refresh'))
    await waitFor(() => expect(result.current.count).toBe(3))
  })
})
