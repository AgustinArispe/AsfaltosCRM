import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ProductsPage } from './ProductsPage'
import type { Product } from '../products/types'

const authState = vi.hoisted(() => ({
  role: 'SUPERVISOR' as 'SUPERVISOR' | 'VENDEDOR',
  logout: vi.fn(),
}))

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({
    token: 'products-token',
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

const initialProducts: Product[] = [
  { id: 1, name: 'SuperPhalt', is_active: true },
  { id: 2, name: 'Bituplast', is_active: true },
  { id: 3, name: 'Producto antiguo', is_active: false },
]

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function mockProductApi({
  products = initialProducts,
  failList,
  duplicateName,
}: {
  products?: Product[]
  failList?: () => boolean
  duplicateName?: string
} = {}) {
  let currentProducts = [...products]
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = new URL(String(input), 'http://localhost')

      if (url.pathname === '/api/products' && !init?.method) {
        if (failList?.()) throw new TypeError('network unavailable')
        const includeInactive = url.searchParams.get('include_inactive') === 'true'
        return jsonResponse(
          200,
          includeInactive
            ? currentProducts
            : currentProducts.filter((product) => product.is_active),
        )
      }

      if (url.pathname === '/api/products' && init?.method === 'POST') {
        const body = JSON.parse(String(init.body)) as { name: string }
        if (body.name === duplicateName) {
          return jsonResponse(409, { detail: 'Product already exists' })
        }
        const created: Product = {
          id: 4,
          name: body.name,
          is_active: true,
        }
        currentProducts = [...currentProducts, created]
        return jsonResponse(201, created)
      }

      const match = /^\/api\/products\/(\d+)$/.exec(url.pathname)
      if (match && init?.method === 'PATCH') {
        const productId = Number(match[1])
        const body = JSON.parse(String(init.body)) as Partial<Product>
        const existing = currentProducts.find((product) => product.id === productId)
        if (!existing) return jsonResponse(404, { detail: 'Not found' })
        const updated = { ...existing, ...body }
        currentProducts = currentProducts.map((product) =>
          product.id === productId ? updated : product,
        )
        return jsonResponse(200, updated)
      }

      throw new Error(`Unexpected request: ${url.pathname}`)
    },
  )
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function rowFor(productName: string): HTMLElement {
  return screen.getByRole('row', { name: new RegExp(productName) })
}

describe('ProductsPage', () => {
  beforeEach(() => {
    authState.role = 'SUPERVISOR'
    authState.logout.mockReset()
  })

  it('lists active and inactive products with derived supervisor counters', async () => {
    const fetchMock = mockProductApi()
    render(<ProductsPage />)

    expect(screen.getByRole('status')).toHaveTextContent('Cargando productos…')
    expect(await screen.findByText('SuperPhalt')).toBeInTheDocument()
    expect(screen.getByText('Producto antiguo')).toBeInTheDocument()
    expect(within(rowFor('SuperPhalt')).getByText('Activo')).toBeInTheDocument()
    expect(within(rowFor('Producto antiguo')).getByText('Inactivo')).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('3 productos · 2 activos · 1 inactivo')
    expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/products?include_inactive=true')
    expect(screen.getByRole('button', { name: 'Editar SuperPhalt' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Desactivar SuperPhalt' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reactivar Producto antiguo' })).toBeInTheDocument()
  })

  it('shows sellers only active products without administration controls', async () => {
    authState.role = 'VENDEDOR'
    const fetchMock = mockProductApi()
    render(<ProductsPage />)

    expect(await screen.findByText('SuperPhalt')).toBeInTheDocument()
    expect(screen.queryByText('Producto antiguo')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Nuevo producto' })).not.toBeInTheDocument()
    expect(screen.queryByRole('columnheader', { name: 'Acciones' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Editar|Desactivar|Reactivar/ })).not.toBeInTheDocument()
    expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/products')
    expect(screen.getByRole('status')).toHaveTextContent('2 productos')
    expect(screen.getByRole('status')).not.toHaveTextContent('inactivos')
  })

  it('renders an empty state and supports retry after a load failure', async () => {
    let shouldFail = false
    mockProductApi({ products: [], failList: () => shouldFail })
    const { unmount } = render(<ProductsPage />)
    expect(await screen.findByRole('heading', { name: 'No hay productos disponibles' })).toBeInTheDocument()
    unmount()

    shouldFail = true
    mockProductApi({ failList: () => shouldFail })
    render(<ProductsPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('No pudimos cargar los productos')
    shouldFail = false
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(await screen.findByText('SuperPhalt')).toBeInTheDocument()
  })

  it('validates, trims and creates a product with accessible focus', async () => {
    const fetchMock = mockProductApi()
    render(<ProductsPage />)
    await screen.findByText('SuperPhalt')

    const trigger = screen.getByRole('button', { name: 'Nuevo producto' })
    trigger.focus()
    fireEvent.click(trigger)
    const dialog = await screen.findByRole('dialog', { name: 'Nuevo producto' })
    await waitFor(() => expect(within(dialog).getByLabelText(/Nombre/)).toHaveFocus())
    fireEvent.click(within(dialog).getByRole('button', { name: 'Crear producto' }))
    expect(await within(dialog).findByText('Ingresá el nombre del producto.')).toBeInTheDocument()
    expect(within(dialog).getByLabelText(/Nombre/)).toHaveAttribute('aria-invalid', 'true')

    fireEvent.change(within(dialog).getByLabelText(/Nombre/), {
      target: { value: '  Asfalto QA  ' },
    })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Crear producto' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(await screen.findByText('Asfalto QA')).toBeInTheDocument()
    expect(trigger).toHaveFocus()

    const postCall = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST')
    expect(JSON.parse(String(postCall?.[1]?.body))).toEqual({ name: 'Asfalto QA' })
  })

  it('keeps duplicate-name errors in the form for correction', async () => {
    mockProductApi({ duplicateName: 'SuperPhalt' })
    render(<ProductsPage />)
    await screen.findByText('SuperPhalt')
    fireEvent.click(screen.getByRole('button', { name: 'Nuevo producto' }))
    const dialog = await screen.findByRole('dialog', { name: 'Nuevo producto' })
    fireEvent.change(within(dialog).getByLabelText(/Nombre/), {
      target: { value: 'SuperPhalt' },
    })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Crear producto' }))

    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Ya existe un producto con ese nombre')
    expect(within(dialog).getByLabelText(/Nombre/)).toHaveValue('SuperPhalt')
  })

  it('reuses the product form for editing only the name', async () => {
    const fetchMock = mockProductApi()
    render(<ProductsPage />)
    await screen.findByText('SuperPhalt')
    fireEvent.click(screen.getByRole('button', { name: 'Editar SuperPhalt' }))
    const dialog = await screen.findByRole('dialog', { name: 'Editar producto' })
    expect(within(dialog).getByLabelText(/Nombre/)).toHaveValue('SuperPhalt')
    expect(within(dialog).queryByLabelText(/Activo|Inactivo/)).not.toBeInTheDocument()
    fireEvent.change(within(dialog).getByLabelText(/Nombre/), {
      target: { value: 'SuperPhalt Plus' },
    })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Guardar cambios' }))

    expect(await screen.findByText('SuperPhalt Plus')).toBeInTheDocument()
    const patchCall = fetchMock.mock.calls.find(([, init]) => init?.method === 'PATCH')
    expect(JSON.parse(String(patchCall?.[1]?.body))).toEqual({ name: 'SuperPhalt Plus' })
  })

  it('confirms deactivation and preserves the product as inactive', async () => {
    const fetchMock = mockProductApi()
    render(<ProductsPage />)
    await screen.findByText('SuperPhalt')
    fireEvent.click(screen.getByRole('button', { name: 'Desactivar SuperPhalt' }))
    const dialog = await screen.findByRole('dialog', { name: '¿Desactivar SuperPhalt?' })
    expect(within(dialog).getByText(/historial comercial/)).toBeInTheDocument()
    await waitFor(() => expect(within(dialog).getByRole('button', { name: 'Cancelar' })).toHaveFocus())
    fireEvent.click(within(dialog).getByRole('button', { name: 'Desactivar producto' }))

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(within(rowFor('SuperPhalt')).getByText('Inactivo')).toBeInTheDocument()
    const statusCall = fetchMock.mock.calls.find(([, init]) =>
      init?.method === 'PATCH' && String(init.body).includes('is_active'),
    )
    expect(JSON.parse(String(statusCall?.[1]?.body))).toEqual({ is_active: false })
  })

  it('reactivates an inactive product directly', async () => {
    mockProductApi()
    render(<ProductsPage />)
    await screen.findByText('Producto antiguo')
    fireEvent.click(screen.getByRole('button', { name: 'Reactivar Producto antiguo' }))

    await waitFor(() =>
      expect(within(rowFor('Producto antiguo')).getByText('Activo')).toBeInTheDocument(),
    )
    expect(screen.getByRole('button', { name: 'Desactivar Producto antiguo' })).toBeInTheDocument()
  })
})
