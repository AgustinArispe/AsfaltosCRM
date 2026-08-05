import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import { AuthProvider } from './auth/AuthContext'
import { SESSION_TOKEN_KEY } from './auth/session-storage'
import type { AuthUser } from './auth/types'
import type { CustomerDetail } from './customers/types'
import type {
  OpportunityDetail,
  OpportunitySummary,
} from './pipeline/types'

const supervisor: AuthUser = {
  id: 1,
  full_name: 'Supervisor FAA',
  email: 'supervisor@faa.test',
  role: 'SUPERVISOR',
  is_active: true,
  created_at: '2026-08-04T12:00:00Z',
  updated_at: '2026-08-04T12:00:00Z',
}

const seller: AuthUser = {
  ...supervisor,
  id: 2,
  full_name: 'Vendedor FAA',
  email: 'vendedor@faa.test',
  role: 'VENDEDOR',
}

const emptyOpportunityPage = {
  items: [],
  page: 1,
  page_size: 100,
  total: 0,
}

const opportunitySummary: OpportunitySummary = {
  id: 77,
  status: 'NUEVA',
  source: 'WEB',
  current_status_entered_at: '2026-08-04T12:00:00Z',
  customer: {
    id: 70,
    name: 'Cliente navegación',
    company: 'Navegación SA',
    email: 'ventas@navegacion.test',
    phone: '1122334455',
    province: 'Buenos Aires',
    legendary_historical_override: false,
  },
  assigned_user: null,
  products: [],
  created_at: '2026-08-04T12:00:00Z',
}

const opportunityDetail: OpportunityDetail = {
  ...opportunitySummary,
  history: [
    {
      id: 1,
      from_status: null,
      to_status: 'NUEVA',
      changed_at: '2026-08-04T12:00:00Z',
      changed_by_user_id: supervisor.id,
    },
  ],
  loss_reason: null,
  updated_at: '2026-08-04T12:00:00Z',
}

const customerDetail: CustomerDetail = {
  ...opportunitySummary.customer,
  created_at: '2026-08-04T12:00:00Z',
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function renderApp(pathname = '/login') {
  window.history.replaceState(null, '', pathname)
  return render(
    <AuthProvider>
      <App />
    </AuthProvider>,
  )
}

function mockRestoredSession(user: AuthUser, token = 'stored-token') {
  window.sessionStorage.setItem(SESSION_TOKEN_KEY, token)
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce(jsonResponse(200, user))
    .mockResolvedValue(jsonResponse(200, emptyOpportunityPage))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

async function fillAndSubmitLogin() {
  fireEvent.change(await screen.findByLabelText('Email'), {
    target: { value: 'supervisor@faa.test' },
  })
  fireEvent.change(screen.getByLabelText('Contraseña'), {
    target: { value: 'correct-password' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Ingresar' }))
}

describe('authenticated frontend', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders the accessible login form', async () => {
    renderApp()

    expect(
      await screen.findByRole('heading', { name: 'Ingresar al sistema' }),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Email')).toHaveAttribute(
      'autocomplete',
      'username',
    )
    expect(screen.getByLabelText('Contraseña')).toHaveAttribute(
      'autocomplete',
      'current-password',
    )
    expect(screen.getByRole('button', { name: 'Ingresar' })).toBeEnabled()
  })

  it('logs in, shows loading, and stores the session token', async () => {
    let resolveLogin!: (response: Response) => void
    const pendingLogin = new Promise<Response>((resolve) => {
      resolveLogin = resolve
    })
    const fetchMock = vi
      .fn()
      .mockReturnValueOnce(pendingLogin)
      .mockResolvedValueOnce(jsonResponse(200, supervisor))
      .mockResolvedValue(jsonResponse(200, emptyOpportunityPage))
    vi.stubGlobal('fetch', fetchMock)
    renderApp()

    await fillAndSubmitLogin()
    expect(
      screen.getByRole('button', { name: 'Ingresando…' }),
    ).toBeDisabled()

    await act(async () => {
      resolveLogin(
        jsonResponse(200, {
          access_token: 'new-token',
          token_type: 'bearer',
          expires_in: 3600,
        }),
      )
    })

    expect(
      await screen.findByRole('heading', { name: 'Pipeline', level: 1 }),
    ).toBeInTheDocument()
    expect(window.location.pathname).toBe('/pipeline')
    expect(window.sessionStorage.getItem(SESSION_TOKEN_KEY)).toBe('new-token')
    expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/auth/login')

    const meRequest = fetchMock.mock.calls[1]?.[1] as RequestInit
    expect(new Headers(meRequest.headers).get('Authorization')).toBe(
      'Bearer new-token',
    )
  })

  it('shows a generic message for invalid credentials', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse(401, { detail: 'Invalid email or password' }))
    vi.stubGlobal('fetch', fetchMock)
    renderApp()

    await fillAndSubmitLogin()

    expect(
      await screen.findByRole('alert'),
    ).toHaveTextContent('El email o la contraseña no son correctos.')
    expect(screen.getByLabelText('Email')).toHaveFocus()
    expect(window.sessionStorage.getItem(SESSION_TOKEN_KEY)).toBeNull()
  })

  it('shows a recoverable message for an unexpected login error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')))
    renderApp()

    await fillAndSubmitLogin()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No pudimos iniciar sesión. Intentá nuevamente.',
    )
  })

  it('restores a valid session without flashing the login page', async () => {
    const fetchMock = mockRestoredSession(supervisor)
    renderApp('/')

    expect(screen.getByRole('status')).toHaveTextContent('Restaurando sesión…')
    expect(
      await screen.findByRole('heading', { name: 'Pipeline', level: 1 }),
    ).toBeInTheDocument()
    expect(screen.getByText('Supervisor FAA')).toBeInTheDocument()
    expect(screen.getByText('Supervisor')).toBeInTheDocument()
    expect(window.location.pathname).toBe('/pipeline')

    const request = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect(new Headers(request.headers).get('Authorization')).toBe(
      'Bearer stored-token',
    )
  })

  it('clears an invalid stored token and redirects to login', async () => {
    window.sessionStorage.setItem(SESSION_TOKEN_KEY, 'invalid-token')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse(401, { detail: 'Invalid token' })),
    )
    renderApp('/customers')

    expect(
      await screen.findByRole('heading', { name: 'Ingresar al sistema' }),
    ).toBeInTheDocument()
    expect(window.sessionStorage.getItem(SESSION_TOKEN_KEY)).toBeNull()
    expect(window.location.pathname).toBe('/login')
  })

  it('protects internal routes when there is no session', async () => {
    renderApp('/products')

    expect(
      await screen.findByRole('heading', { name: 'Ingresar al sistema' }),
    ).toBeInTheDocument()
    expect(window.location.pathname).toBe('/login')
  })

  it('shows Users navigation to supervisors', async () => {
    mockRestoredSession(supervisor)
    renderApp('/pipeline')

    expect(
      await screen.findByRole('link', { name: 'Usuarios' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Clientes' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Productos' })).toBeInTheDocument()
  })

  it('opens the pipeline drawer, restores focus, and keeps the deep-link route', async () => {
    window.sessionStorage.setItem(SESSION_TOKEN_KEY, 'stored-token')
    const fetchMock = vi.fn(
      async (input: RequestInfo | URL): Promise<Response> => {
        const url = new URL(String(input), 'http://localhost')
        if (url.pathname === '/api/auth/me') {
          return jsonResponse(200, supervisor)
        }
        if (url.pathname === '/api/opportunities/77') {
          return jsonResponse(200, opportunityDetail)
        }
        if (url.pathname === '/api/opportunities') {
          const status = url.searchParams.get('status')
          return jsonResponse(200, {
            ...emptyOpportunityPage,
            items: status === 'NUEVA' ? [opportunitySummary] : [],
            total: status === 'NUEVA' ? 1 : 0,
          })
        }
        throw new Error(`Unexpected request: ${url.pathname}`)
      },
    )
    vi.stubGlobal('fetch', fetchMock)
    renderApp('/pipeline')

    const cardButton = await screen.findByRole('button', {
      name: /Abrir detalle de la oportunidad de Cliente navegación/,
    })
    cardButton.focus()
    fireEvent.click(cardButton)

    expect(window.location.pathname).toBe('/pipeline')
    const drawer = await screen.findByRole('dialog', {
      name: 'Detalle de oportunidad',
    })
    expect(
      within(drawer).getByRole('heading', { name: 'Navegación SA' }),
    ).toBeInTheDocument()
    fireEvent(drawer, new Event('cancel', { cancelable: true }))
    await waitFor(() => expect(cardButton).toHaveFocus())

    act(() => {
      window.history.pushState(null, '', '/opportunities/77')
      window.dispatchEvent(new PopStateEvent('popstate'))
    })

    expect(
      await screen.findByRole('heading', { name: 'Navegación SA' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'Detalle de oportunidad', level: 1 }),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Pipeline' })).toHaveAttribute(
      'aria-current',
      'page',
    )

    fireEvent.click(screen.getByRole('link', { name: 'Volver al Pipeline' }))

    expect(window.location.pathname).toBe('/pipeline')
    expect(
      await screen.findByRole('heading', { name: 'Nuevos' }),
    ).toBeInTheDocument()
  })

  it('hides Users and redirects its route for sellers', async () => {
    mockRestoredSession(seller)
    renderApp('/users')

    expect(
      await screen.findByRole('heading', { name: 'Pipeline', level: 1 }),
    ).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Usuarios' })).not.toBeInTheDocument()
    expect(window.location.pathname).toBe('/pipeline')
  })

  it('opens the dynamic customer detail route and keeps Customers active', async () => {
    window.sessionStorage.setItem(SESSION_TOKEN_KEY, 'stored-token')
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL): Promise<Response> => {
        const url = new URL(String(input), 'http://localhost')
        if (url.pathname === '/api/auth/me') return jsonResponse(200, supervisor)
        if (url.pathname === '/api/customers/70') return jsonResponse(200, customerDetail)
        if (url.pathname === '/api/opportunities') return jsonResponse(200, emptyOpportunityPage)
        throw new Error(`Unexpected request: ${url.pathname}`)
      }),
    )
    renderApp('/customers/70')

    expect(await screen.findByRole('heading', { name: 'Cliente navegación' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Ficha de cliente', level: 1 })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Clientes' })).toHaveAttribute('aria-current', 'page')
  })

  it('logs out, clears storage, and returns to login', async () => {
    mockRestoredSession(supervisor)
    renderApp('/pipeline')
    await screen.findByRole('heading', { name: 'Pipeline', level: 1 })

    fireEvent.click(screen.getByRole('button', { name: 'Cerrar sesión' }))

    await waitFor(() => expect(window.location.pathname).toBe('/login'))
    expect(
      screen.getByRole('heading', { name: 'Ingresar al sistema' }),
    ).toBeInTheDocument()
    expect(window.sessionStorage.getItem(SESSION_TOKEN_KEY)).toBeNull()
  })
})
