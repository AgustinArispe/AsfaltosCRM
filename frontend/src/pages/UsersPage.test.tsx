import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { AuthUser } from '../auth/types'
import { UsersPage } from './UsersPage'

const logout = vi.fn()

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({ token: 'users-token', logout }),
}))

const supervisor: AuthUser = {
  id: 1,
  full_name: 'Supervisor FAA',
  email: 'supervisor@faa.test',
  role: 'SUPERVISOR',
  is_active: true,
  created_at: '2026-08-18T12:00:00Z',
  updated_at: '2026-08-18T12:00:00Z',
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function mockUsersApi() {
  let users = [supervisor]
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), 'http://localhost')
    if (url.pathname === '/api/users' && !init?.method) return jsonResponse(200, users)
    if (url.pathname === '/api/users' && init?.method === 'POST') {
      const payload = JSON.parse(String(init.body)) as {
        full_name: string
        email: string
        role: AuthUser['role']
      }
      const created = { ...supervisor, ...payload, id: 2, is_active: true }
      users = [...users, created]
      return jsonResponse(201, created)
    }
    const passwordMatch = /^\/api\/users\/(\d+)\/password$/.exec(url.pathname)
    if (passwordMatch && init?.method === 'PUT') {
      return jsonResponse(
        200,
        users.find((item) => item.id === Number(passwordMatch[1])),
      )
    }
    const userMatch = /^\/api\/users\/(\d+)$/.exec(url.pathname)
    if (userMatch && init?.method === 'PATCH') {
      const id = Number(userMatch[1])
      const payload = JSON.parse(String(init.body)) as Partial<AuthUser>
      users = users.map((item) => (item.id === id ? { ...item, ...payload } : item))
      return jsonResponse(
        200,
        users.find((item) => item.id === id),
      )
    }
    throw new Error(`Unexpected request: ${url.pathname}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('UsersPage', () => {
  beforeEach(() => logout.mockReset())

  it('uses the existing supervisor contracts for create, edit, password and activation', async () => {
    const fetchMock = mockUsersApi()
    render(<UsersPage />)
    expect(await screen.findByText('Supervisor FAA')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Nuevo usuario' }))
    let dialog = await screen.findByRole('dialog', { name: 'Nuevo usuario' })
    fireEvent.change(within(dialog).getByLabelText('Nombre completo'), {
      target: { value: 'Vendedora FAA' },
    })
    fireEvent.change(within(dialog).getByLabelText('Email'), {
      target: { value: 'vendedora@faa.test' },
    })
    fireEvent.change(within(dialog).getByLabelText('Contraseña inicial'), {
      target: { value: 'segura-123' },
    })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Guardar usuario' }))
    expect(await screen.findByText('Vendedora FAA')).toBeInTheDocument()

    const row = screen.getByRole('row', { name: /Vendedora FAA/ })
    fireEvent.click(within(row).getByRole('button', { name: 'Editar' }))
    dialog = await screen.findByRole('dialog', { name: 'Editar usuario' })
    fireEvent.change(within(dialog).getByLabelText('Nombre completo'), {
      target: { value: 'Vendedora Norte' },
    })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Guardar usuario' }))
    expect(await screen.findByText('Vendedora Norte')).toBeInTheDocument()

    const updatedRow = screen.getByRole('row', { name: /Vendedora Norte/ })
    fireEvent.click(within(updatedRow).getByRole('button', { name: 'Contraseña' }))
    dialog = await screen.findByRole('dialog', { name: 'Reemplazar contraseña' })
    fireEvent.change(within(dialog).getByLabelText('Nueva contraseña'), {
      target: { value: 'nueva-1234' },
    })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Reemplazar' }))
    await waitFor(() =>
      expect(
        screen.queryByRole('dialog', { name: 'Reemplazar contraseña' }),
      ).not.toBeInTheDocument(),
    )

    fireEvent.click(within(updatedRow).getByRole('button', { name: 'Desactivar' }))
    dialog = await screen.findByRole('dialog', { name: 'Desactivar acceso' })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Desactivar usuario' }))
    await waitFor(() => expect(within(updatedRow).getByText('Inactivo')).toBeInTheDocument())

    expect(fetchMock.mock.calls.some(([, options]) => options?.method === 'POST')).toBe(true)
    expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith('/password'))).toBe(true)
  })

  it('shows a recoverable loading error and an intentional empty state', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValueOnce(new TypeError('offline')))
    const { unmount } = render(<UsersPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('offline')
    unmount()

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(200, [])))
    render(<UsersPage />)
    expect(
      await screen.findByRole('heading', { name: 'Todavía no hay usuarios' }),
    ).toBeInTheDocument()
  })
})
