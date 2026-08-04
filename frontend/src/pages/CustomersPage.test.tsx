import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { CustomersPage } from './CustomersPage'
import type { CustomerSummary } from '../customers/types'

const authState = vi.hoisted(() => ({
  role: 'SUPERVISOR' as 'SUPERVISOR' | 'VENDEDOR',
  logout: vi.fn(),
}))

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({
    token: 'customers-token',
    logout: authState.logout,
    user: {
      id: 1,
      full_name: 'Usuario FAA',
      email: 'usuario@faa.test',
      role: authState.role,
      is_active: true,
    },
  }),
}))

const customers: CustomerSummary[] = [
  {
    id: 1,
    name: 'Constructora Austral',
    company: 'Austral SA',
    email: 'ventas@austral.test',
    phone: '+54 11 4444-5555',
    province: 'Buenos Aires',
    legendary_historical_override: true,
  },
  {
    id: 2,
    name: 'Cliente Norte',
    company: null,
    email: null,
    phone: '3815550000',
    province: 'Tucumán',
    legendary_historical_override: false,
  },
]

function jsonResponse(status: number, body: unknown): Response {
  if (status === 204) return new Response(null, { status })
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function mockCustomerApi({
  initialCustomers = customers,
  total = initialCustomers.length,
  failList,
}: {
  initialCustomers?: CustomerSummary[]
  total?: number
  failList?: () => boolean
} = {}) {
  let currentCustomers = [...initialCustomers]
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = new URL(String(input), 'http://localhost')

      if (url.pathname === '/api/customers' && !init?.method) {
        if (failList?.()) throw new TypeError('network unavailable')
        const search = url.searchParams.get('search')?.toLocaleLowerCase('es-AR')
        const filtered = search
          ? currentCustomers.filter((customer) =>
              [customer.name, customer.company, customer.email, customer.phone]
                .filter(Boolean)
                .some((value) => value?.toLocaleLowerCase('es-AR').includes(search)),
            )
          : currentCustomers
        return jsonResponse(200, {
          items: filtered,
          page: Number(url.searchParams.get('page')),
          page_size: Number(url.searchParams.get('page_size')),
          total: search ? filtered.length : total,
        })
      }

      if (url.pathname === '/api/customers' && init?.method === 'POST') {
        const body = JSON.parse(String(init.body)) as Omit<CustomerSummary, 'id'>
        const created = { id: 3, ...body }
        currentCustomers = [...currentCustomers, created]
        return jsonResponse(201, created)
      }

      const customerMatch = /^\/api\/customers\/(\d+)$/.exec(url.pathname)
      if (customerMatch && init?.method === 'PATCH') {
        const customerId = Number(customerMatch[1])
        const body = JSON.parse(String(init.body)) as Partial<CustomerSummary>
        const existing = currentCustomers.find((customer) => customer.id === customerId)
        if (!existing) return jsonResponse(404, { detail: 'Not found' })
        const updated = { ...existing, ...body }
        currentCustomers = currentCustomers.map((customer) =>
          customer.id === customerId ? updated : customer,
        )
        return jsonResponse(200, updated)
      }

      if (customerMatch && init?.method === 'DELETE') {
        const customerId = Number(customerMatch[1])
        currentCustomers = currentCustomers.filter((customer) => customer.id !== customerId)
        return jsonResponse(204, null)
      }

      throw new Error(`Unexpected request: ${url.pathname}`)
    },
  )
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('CustomersPage', () => {
  beforeEach(() => {
    authState.role = 'SUPERVISOR'
    authState.logout.mockReset()
  })

  it('loads a compact customer table with columns, links and pagination metadata', async () => {
    mockCustomerApi()
    render(<CustomersPage />)

    expect(screen.getByRole('status')).toHaveTextContent('Cargando clientes…')
    expect(await screen.findByRole('link', { name: 'Constructora Austral' })).toHaveAttribute('href', '/customers/1')
    expect(screen.getByRole('columnheader', { name: 'Empresa' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Categoría' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'ventas@austral.test' })).toHaveAttribute('href', 'mailto:ventas@austral.test')
    expect(screen.getByRole('link', { name: '+54 11 4444-5555' })).toHaveAttribute('href', 'tel:+541144445555')
    expect(screen.getByText('Legendario')).toBeInTheDocument()
    expect(screen.getByText('2 clientes')).toBeInTheDocument()
    expect(screen.getByText('Página 1 de 1')).toBeInTheDocument()
  })

  it('debounces API search and shows a useful no-results state', async () => {
    const fetchMock = mockCustomerApi()
    render(<CustomersPage />)
    await screen.findByRole('link', { name: 'Constructora Austral' })

    fireEvent.change(screen.getByLabelText('Buscar clientes'), {
      target: { value: 'inexistente' },
    })

    expect(await screen.findByRole('heading', { name: 'No encontramos clientes' })).toBeInTheDocument()
    expect(screen.getByText(/Probá con otro nombre/)).toBeInTheDocument()
    expect(
      fetchMock.mock.calls.some(([input]) =>
        String(input).includes('search=inexistente'),
      ),
    ).toBe(true)
  })

  it('shows an empty state and offers retry after a request error', async () => {
    let shouldFail = false
    mockCustomerApi({ initialCustomers: [], failList: () => shouldFail })
    const { unmount } = render(<CustomersPage />)
    expect(await screen.findByRole('heading', { name: 'Todavía no hay clientes' })).toBeInTheDocument()
    unmount()

    shouldFail = true
    mockCustomerApi({ failList: () => shouldFail })
    render(<CustomersPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('No pudimos cargar los clientes')
    shouldFail = false
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(await screen.findByRole('link', { name: 'Constructora Austral' })).toBeInTheDocument()
  })

  it('opens the shared form, validates fields, creates and refreshes the list', async () => {
    const fetchMock = mockCustomerApi()
    render(<CustomersPage />)
    await screen.findByRole('link', { name: 'Constructora Austral' })

    fireEvent.click(screen.getByRole('button', { name: 'Nuevo cliente' }))
    const dialog = await screen.findByRole('dialog', { name: 'Nuevo cliente' })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Crear cliente' }))
    expect(await within(dialog).findByText('Ingresá el nombre del cliente.')).toBeInTheDocument()

    fireEvent.change(within(dialog).getByLabelText(/Nombre/), { target: { value: '  Cliente Nuevo  ' } })
    fireEvent.change(within(dialog).getByLabelText('Email'), { target: { value: 'email-invalido' } })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Crear cliente' }))
    expect(await within(dialog).findByText('Ingresá un email válido.')).toBeInTheDocument()
    expect(within(dialog).getByLabelText('Email')).toHaveFocus()

    fireEvent.change(within(dialog).getByLabelText('Email'), { target: { value: 'nuevo@faa.test' } })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Crear cliente' }))

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(await screen.findByRole('link', { name: 'Cliente Nuevo' })).toBeInTheDocument()
    const postCall = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST')
    expect(JSON.parse(String(postCall?.[1]?.body))).toMatchObject({
      name: 'Cliente Nuevo',
      email: 'nuevo@faa.test',
      legendary_historical_override: false,
    })
  })

  it('reuses the form for editing and keeps API errors recoverable', async () => {
    const fetchMock = mockCustomerApi()
    render(<CustomersPage />)
    await screen.findByRole('link', { name: 'Constructora Austral' })

    fireEvent.click(screen.getByRole('button', { name: 'Editar a Constructora Austral' }))
    const dialog = await screen.findByRole('dialog', { name: 'Editar cliente' })
    expect(within(dialog).getByLabelText(/Nombre/)).toHaveValue('Constructora Austral')
    expect(within(dialog).getByLabelText('Empresa')).toHaveValue('Austral SA')
    fireEvent.change(within(dialog).getByLabelText('Empresa'), { target: { value: 'Austral Renovada SA' } })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Guardar cambios' }))

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(await screen.findByText('Austral Renovada SA')).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'PATCH')).toBe(true)
  })

  it('shows supervisor-only legendary and delete controls, but hides them from sellers', async () => {
    mockCustomerApi()
    const { unmount } = render(<CustomersPage />)
    await screen.findByRole('link', { name: 'Constructora Austral' })
    expect(screen.getByRole('button', { name: 'Eliminar a Constructora Austral' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Nuevo cliente' }))
    expect(await screen.findByLabelText(/Legendario histórico/)).toBeInTheDocument()
    unmount()

    authState.role = 'VENDEDOR'
    mockCustomerApi()
    render(<CustomersPage />)
    await screen.findByRole('link', { name: 'Constructora Austral' })
    expect(screen.queryByRole('button', { name: /Eliminar a/ })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Nuevo cliente' }))
    expect(screen.queryByLabelText(/Legendario histórico/)).not.toBeInTheDocument()
  })

  it('confirms soft delete and removes the customer from the refreshed list', async () => {
    const fetchMock = mockCustomerApi()
    render(<CustomersPage />)
    await screen.findByRole('link', { name: 'Constructora Austral' })

    fireEvent.click(screen.getByRole('button', { name: 'Eliminar a Constructora Austral' }))
    const dialog = await screen.findByRole('dialog', { name: '¿Eliminar a Constructora Austral?' })
    expect(within(dialog).getByText(/historial comercial se conservará/)).toBeInTheDocument()
    expect(within(dialog).getByRole('button', { name: 'Cancelar' })).toHaveFocus()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Eliminar cliente' }))

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    await waitFor(() => expect(screen.queryByRole('link', { name: 'Constructora Austral' })).not.toBeInTheDocument())
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'DELETE')).toBe(true)
  })

  it('uses simple previous and next pagination controls', async () => {
    const fetchMock = mockCustomerApi({ total: 21 })
    render(<CustomersPage />)
    await screen.findByText('Página 1 de 2')
    expect(screen.getByRole('button', { name: 'Anterior' })).toBeDisabled()

    fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(([input]) => String(input).includes('page=2')),
      ).toBe(true),
    )
    expect(screen.getByText('Página 2 de 2')).toBeInTheDocument()
  })
})
