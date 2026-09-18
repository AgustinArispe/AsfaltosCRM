import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { useState } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { NotificationAttentionProvider } from '../notifications/NotificationAttention'
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

const olderActive = {
  ...olderResolved,
  id: 4,
  resolved_at: null,
  opportunity: {
    ...olderResolved.opportunity,
    id: 40,
    customer: { ...olderResolved.opportunity.customer, name: 'Obra para retomar' },
  },
}

const newLead = {
  ...newer,
  id: 3,
  type: 'NEW_LEAD' as const,
  opportunity: {
    ...newer.opportunity,
    id: 30,
    customer: { ...newer.opportunity.customer, name: 'Lead web' },
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
    if (url.pathname === '/api/notifications/2/read-state') {
      const isRead = JSON.parse(String(init?.body)).is_read as boolean
      return Promise.resolve(
        failRead
          ? response({ detail: 'fail' }, 500)
          : response({ ...newer, read_at: isRead ? '2026-08-14T15:00:00Z' : null }),
      )
    }
    if (url.pathname === '/api/notifications/1/read-state') {
      const isRead = JSON.parse(String(init?.body)).is_read as boolean
      return Promise.resolve(
        response({ ...olderResolved, read_at: isRead ? olderResolved.read_at : null }),
      )
    }
    if (url.pathname === '/api/notifications/4/read-state') {
      const isRead = JSON.parse(String(init?.body)).is_read as boolean
      return Promise.resolve(
        response({ ...olderActive, read_at: isRead ? olderActive.read_at : null }),
      )
    }
    if (url.pathname === '/api/notifications/read-all')
      return Promise.resolve(response({ updated_count: 1 }))
    return Promise.reject(new Error(`Unexpected ${url.pathname}`))
  })
}

function PageWithAttention({ initialCount = 1 }: { initialCount?: number }) {
  const [count, setCount] = useState(initialCount)
  return (
    <NotificationAttentionProvider
      value={{
        adjustCount: (delta) => setCount((current) => Math.max(0, current + delta)),
        count,
        refresh: vi.fn(),
      }}
    >
      <output aria-label='Contador sin leer'>{count}</output>
      <NotificationsPage />
    </NotificationAttentionProvider>
  )
}

describe('NotificationsPage', () => {
  beforeEach(() => window.history.replaceState(null, '', '/notifications'))

  it('labels a new lead and opens its Opportunity', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL) => {
        const url = new URL(String(input), 'http://localhost')
        if (url.pathname === '/api/notifications/3/read') {
          return Promise.resolve(response({ ...newLead, read_at: '2026-08-14T15:00:00Z' }))
        }
        return Promise.resolve(response({ items: [newLead], page: 1, page_size: 25, total: 1 }))
      }),
    )
    render(<NotificationsPage />)

    fireEvent.click(
      await screen.findByRole('button', { name: /Nueva oportunidad recibida: Lead web/ }),
    )

    await waitFor(() => expect(window.location.pathname).toBe('/pipeline/opportunities/30'))
  })

  it('renders newest-first history and switches to unread history', async () => {
    vi.stubGlobal('fetch', mockApi())
    render(<NotificationsPage />)
    const rows = await screen.findAllByRole('button', { name: /¡Atrasado!/ })
    expect(rows[0]).toHaveAccessibleName(/Obra nueva/)
    expect(screen.getByText('Resuelta')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Sin leer' }))
    expect(
      await screen.findByRole('button', { name: /¡Atrasado!: Obra nueva/ }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /¡Atrasado!: Obra histórica/ }),
    ).not.toBeInTheDocument()
  })

  it('acknowledges an unread notification without removing history and navigates by status', async () => {
    const fetchMock = mockApi()
    vi.stubGlobal('fetch', fetchMock)
    render(<NotificationsPage />)
    const row = await screen.findByRole('button', { name: /¡Atrasado!: Obra nueva/ })
    fireEvent.keyDown(row, { key: 'Enter' })
    fireEvent.click(row)
    await waitFor(() => expect(window.location.pathname).toBe('/pipeline/opportunities/20'))
    expect((await screen.findAllByText('Leída')).length).toBeGreaterThan(1)
    expect(screen.getByRole('button', { name: /¡Atrasado!: Obra histórica/ })).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith('/api/notifications/2/read', expect.any(Object))
  })

  it('changes unread to read in place and synchronizes the active counter', async () => {
    const fetchMock = mockApi()
    vi.stubGlobal('fetch', fetchMock)
    render(<PageWithAttention />)
    const row = await screen.findByRole('button', { name: /¡Atrasado!: Obra nueva/ })
    expect(row).toHaveClass('notification-row--unread')

    fireEvent.click(
      screen.getByRole('button', { name: 'Marcar como leída: Obra nueva · Constructora FAA' }),
    )

    await waitFor(() => expect(row).not.toHaveClass('notification-row--unread'))
    expect(
      screen.getByRole('button', { name: 'Marcar como no leída: Obra nueva · Constructora FAA' }),
    ).toHaveAttribute('title', 'Marcar como no leída')
    expect(screen.getByLabelText('Contador sin leer')).toHaveTextContent('0')
    expect(window.location.pathname).toBe('/notifications')
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/notifications/2/read-state',
      expect.objectContaining({ method: 'PUT' }),
    )
  })

  it('changes read to unread without navigation and leaves resolved attention unchanged', async () => {
    vi.stubGlobal('fetch', mockApi())
    render(<PageWithAttention />)
    const historic = await screen.findByRole('button', { name: /¡Atrasado!: Obra histórica/ })
    expect(historic).not.toHaveClass('notification-row--unread')

    fireEvent.click(screen.getByRole('button', { name: 'Marcar como no leída: Obra histórica' }))

    await waitFor(() => expect(historic).toHaveClass('notification-row--unread'))
    expect(
      screen.getByRole('button', { name: 'Marcar como leída: Obra histórica' }),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Contador sin leer')).toHaveTextContent('1')
    expect(window.location.pathname).toBe('/notifications')
  })

  it('increments active attention when a read active notification becomes unread', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = new URL(String(input), 'http://localhost')
        if (url.pathname === '/api/notifications/4/read-state') {
          const isRead = JSON.parse(String(init?.body)).is_read as boolean
          return Promise.resolve(
            response({ ...olderActive, read_at: isRead ? olderActive.read_at : null }),
          )
        }
        return Promise.resolve(response({ items: [olderActive], page: 1, page_size: 25, total: 1 }))
      }),
    )
    render(<PageWithAttention initialCount={0} />)

    fireEvent.click(
      await screen.findByRole('button', { name: /^Marcar como no leída: Obra para retomar/ }),
    )

    await screen.findByRole('button', { name: /^Marcar como leída: Obra para retomar/ })
    expect(screen.getByLabelText('Contador sin leer')).toHaveTextContent('1')
  })

  it('uses the accessible Pipeline route and keeps acknowledgement failures visible', async () => {
    vi.stubGlobal('fetch', mockApi({ failRead: true }))
    render(<NotificationsPage />)
    const historic = await screen.findByRole('button', { name: /¡Atrasado!: Obra histórica/ })
    fireEvent.click(historic)
    expect(window.location.pathname).toBe('/pipeline/opportunities/10')
    window.history.replaceState(null, '', '/notifications')
    const unread = screen.getByRole('button', { name: /¡Atrasado!: Obra nueva/ })
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
      await screen.findByRole('heading', { name: 'No tenés notificaciones por ahora' }),
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
    expect(screen.getByRole('button', { name: /¡Atrasado!: Obra histórica/ })).toBeInTheDocument()
  })

  it('removes acknowledged active items immediately from the unread view', async () => {
    vi.stubGlobal('fetch', mockApi())
    render(<NotificationsPage />)
    fireEvent.click(await screen.findByRole('button', { name: 'Sin leer' }))
    await screen.findByRole('button', { name: /¡Atrasado!: Obra nueva/ })
    fireEvent.click(screen.getByRole('button', { name: 'Marcar activas como leídas' }))
    expect(
      await screen.findByRole('heading', { name: 'Sin notificaciones sin leer' }),
    ).toBeInTheDocument()
  })
})
