import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { NotificationsPage } from './NotificationsPage'

const authState = { token: 'token', logout: vi.fn() }

vi.mock('../auth/AuthContext', () => ({ useAuth: () => authState }))

const newer = {
  id: 2,
  type: 'OPPORTUNITY_STALE' as const,
  created_at: '2026-08-14T14:00:00Z',
  read_at: null,
  resolved_at: null,
  opportunity: {
    id: 20,
    status: 'NUEVA' as const,
    current_status_entered_at: '2026-07-30T14:00:00Z',
    customer: { id: 2, name: 'Obra nueva', company: 'Constructora FAA' },
  },
}

const olderResolved = {
  id: 1,
  type: 'OPPORTUNITY_STALE' as const,
  created_at: '2026-08-13T14:00:00Z',
  read_at: '2026-08-13T15:00:00Z',
  resolved_at: '2026-08-13T16:00:00Z',
  opportunity: {
    id: 10,
    status: 'PERDIDA' as const,
    current_status_entered_at: '2026-08-13T13:00:00Z',
    customer: { id: 1, name: 'Obra histórica', company: 'Obra histórica' },
  },
}

function response(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function mockApi({
  failRead = false,
  failInitial = false,
}: {
  failRead?: boolean
  failInitial?: boolean
} = {}) {
  return vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), 'http://localhost')
    if (url.pathname === '/api/notifications' && init?.method !== 'POST') {
      if (failInitial) return Promise.resolve(response({ detail: 'fail' }, 500))
      const unreadOnly = url.searchParams.get('unread_only') === 'true'
      return Promise.resolve(
        response({
          items:
            unreadOnly && url.searchParams.get('include_resolved') === 'true'
              ? [newer]
              : [newer, olderResolved],
          page: 1,
          page_size: 25,
          total: unreadOnly && url.searchParams.get('include_resolved') === 'true' ? 1 : 2,
        }),
      )
    }
    if (url.pathname === '/api/notifications/2/read') {
      return Promise.resolve(
        failRead
          ? response({ detail: 'fail' }, 500)
          : response({ ...newer, read_at: '2026-08-14T15:00:00Z' }),
      )
    }
    if (url.pathname === '/api/notifications/read-all')
      return Promise.resolve(response({ updated_count: 1 }))
    return Promise.reject(new Error(`Unexpected ${url.pathname}`))
  })
}

describe('NotificationsPage', () => {
  it('renders newest-first history and switches to unread history', async () => {
    vi.stubGlobal('fetch', mockApi())
    render(<NotificationsPage />)
    const rows = await screen.findAllByRole('button', { name: /Seguimiento pendiente/ })
    expect(rows[0]).toHaveAccessibleName(/Obra nueva/)
    expect(screen.getByText('Resuelta')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Sin leer' }))
    expect(await screen.findByRole('button', { name: /Obra nueva/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Obra histórica/ })).not.toBeInTheDocument()
  })

  it('acknowledges an unread notification without removing history and navigates by status', async () => {
    const fetchMock = mockApi()
    vi.stubGlobal('fetch', fetchMock)
    render(<NotificationsPage />)
    const row = await screen.findByRole('button', { name: /Obra nueva/ })
    fireEvent.keyDown(row, { key: 'Enter' })
    fireEvent.click(row)
    await waitFor(() => expect(window.location.pathname).toBe('/pipeline/opportunities/20'))
    expect((await screen.findAllByText('Leída')).length).toBeGreaterThan(1)
    expect(screen.getByRole('button', { name: /Obra histórica/ })).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith('/api/notifications/2/read', expect.any(Object))
  })

  it('uses the lost canonical route and keeps acknowledgement failures visible', async () => {
    vi.stubGlobal('fetch', mockApi({ failRead: true }))
    render(<NotificationsPage />)
    const historic = await screen.findByRole('button', { name: /Obra histórica/ })
    fireEvent.click(historic)
    expect(window.location.pathname).toBe('/lost/opportunities/10')
    window.history.replaceState(null, '', '/notifications')
    const unread = screen.getByRole('button', { name: /Obra nueva/ })
    fireEvent.click(unread)
    expect(await screen.findByRole('alert')).toHaveTextContent('No pudimos guardar la lectura')
  })

  it('shows distinct empty and initial-error states', async () => {
    vi.stubGlobal('fetch', mockApi({ failInitial: true }))
    render(<NotificationsPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No pudimos cargar las notificaciones',
    )
  })

  it('distinguishes empty history from an empty unread view', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL) => {
        const url = new URL(String(input), 'http://localhost')
        return Promise.resolve(
          response({
            items: [],
            page: 1,
            page_size: 25,
            total: 0,
            include_resolved: url.searchParams.get('include_resolved'),
          }),
        )
      }),
    )
    render(<NotificationsPage />)
    expect(
      await screen.findByRole('heading', { name: 'Sin historial de notificaciones' }),
    ).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Sin leer' }))
    expect(
      await screen.findByRole('heading', { name: 'Sin notificaciones sin leer' }),
    ).toBeInTheDocument()
  })

  it('uses the active-only bulk acknowledgement command without deleting loaded history', async () => {
    const fetchMock = mockApi()
    vi.stubGlobal('fetch', fetchMock)
    render(<NotificationsPage />)
    fireEvent.click(await screen.findByRole('button', { name: 'Marcar activas como leídas' }))
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith('/api/notifications/read-all', expect.any(Object)),
    )
    expect(screen.getByRole('button', { name: /Obra histórica/ })).toBeInTheDocument()
  })
})
