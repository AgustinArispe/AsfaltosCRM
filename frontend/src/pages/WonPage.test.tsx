import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { WonPage } from './WonPage'

const logout = vi.hoisted(() => vi.fn())

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({ token: 'token', logout, user: { role: 'SUPERVISOR' } }),
}))

function json(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('WonPage', () => {
  beforeEach(() => {
    logout.mockReset()
    window.history.replaceState(null, '', '/won')
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = new URL(String(input), 'http://localhost')
        if (url.pathname.endsWith('/filter-options'))
          return json({ products: [], provinces: ['Cordoba'], responsible_users: [] })
        if (url.pathname.endsWith('/statistics'))
          return json({ won_count: 0, won_quantity_kg: '0.000' })
        return json({ items: [], next_cursor: null })
      }),
    )
  })

  it('defaults to the Buenos Aires current month and supports all history', async () => {
    render(<WonPage />)
    expect(screen.getByLabelText('Período')).toHaveValue('month')
    await waitFor(() => expect(fetch).toHaveBeenCalled())
    const firstList = (fetch as ReturnType<typeof vi.fn>).mock.calls.find(([value]) =>
      String(value).includes('/won-opportunities?'),
    )
    expect(String(firstList?.[0])).toContain('won_from=')
    fireEvent.change(screen.getByLabelText('Período'), { target: { value: 'all' } })
    fireEvent.click(screen.getByRole('button', { name: 'Aplicar' }))
    await waitFor(() => expect(window.location.search).toContain('period=all'))
    const calls = (fetch as ReturnType<typeof vi.fn>).mock.calls.map(([value]) => String(value))
    expect(calls.at(-2)).not.toContain('won_from=')
  })

  it('restores supported URL filters and serializes a custom inclusive end date', async () => {
    window.history.replaceState(
      null,
      '',
      '/won?period=custom&from=2026-08-01&to=2026-08-31&province=Cordoba',
    )
    render(<WonPage />)
    await waitFor(() => expect(screen.getByLabelText('Provincia')).toHaveValue('Cordoba'))
    await waitFor(() => expect(fetch).toHaveBeenCalled())
    const calls = (fetch as ReturnType<typeof vi.fn>).mock.calls.map(([value]) =>
      decodeURIComponent(String(value)),
    )
    expect(calls.some((value) => value.includes('won_from=2026-08-01T00:00:00-03:00'))).toBe(true)
    expect(calls.some((value) => value.includes('won_to=2026-09-01'))).toBe(true)
  })

  it('filters, paginates, opens detail, and resets a populated history', async () => {
    const item = {
      opportunity: {
        id: 41,
        status: 'GANADA',
        source: 'WEB',
        current_status_entered_at: '2026-09-07T12:00:00Z',
        customer: {
          id: 9,
          name: 'Vial Sur',
          company: 'Vial Sur SA',
          email: null,
          phone: null,
          province: 'Cordoba',
          legendary_historical_override: false,
          is_legendary: false,
        },
        assigned_user: { id: 7, full_name: 'Ana Venta', email: 'ana@faa.test' },
        products: [
          { product: { id: 3, name: 'CAC D19', is_active: false }, quantity_kg: '123.000' },
        ],
        created_at: '2026-09-01T12:00:00Z',
      },
      won_at: '2026-09-07T12:00:00Z',
      won_total_kg: '123.000',
    }
    let pageCalls = 0
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = new URL(String(input), 'http://localhost')
        if (url.pathname.endsWith('/filter-options'))
          return json({
            products: [{ id: 3, name: 'CAC D19', is_active: false }],
            provinces: ['Cordoba'],
            responsible_users: [{ id: 7, full_name: 'Ana Venta', is_active: false }],
          })
        if (url.pathname.endsWith('/statistics'))
          return json({ won_count: 1, won_quantity_kg: '123.000' })
        pageCalls += 1
        const isNextPage = url.searchParams.has('cursor')
        return json({
          items: [isNextPage ? { ...item, opportunity: { ...item.opportunity, id: 42 } } : item],
          next_cursor: isNextPage ? null : 'next-page',
        })
      }),
    )
    render(<WonPage />)
    expect(await screen.findByText('Vial Sur SA')).toBeVisible()
    const summary = screen.getByRole('region', { name: 'Resumen de Ganadas' })
    expect(within(summary).getByText('1 oportunidad')).toBeVisible()
    expect(within(summary).getByText('123 kg')).toBeVisible()
    fireEvent.change(screen.getByLabelText('Buscar cliente, empresa o ID'), {
      target: { value: ' Vial ' },
    })
    fireEvent.change(screen.getByLabelText('Producto'), { target: { value: '3' } })
    fireEvent.change(screen.getByLabelText('Origen'), { target: { value: 'WEB' } })
    fireEvent.change(screen.getByLabelText('Provincia'), { target: { value: 'Cordoba' } })
    fireEvent.change(screen.getByLabelText('Responsable'), { target: { value: 'unassigned' } })
    fireEvent.click(screen.getByRole('button', { name: 'Aplicar' }))
    await waitFor(() => expect(window.location.search).toContain('search=Vial'))
    fireEvent.click(screen.getByRole('button', { name: 'Cargar más' }))
    await waitFor(() => expect(pageCalls).toBeGreaterThan(1))
    const openButton = screen.getByRole('button', {
      name: 'Abrir oportunidad 41 de Vial Sur',
    })
    openButton.focus()
    expect(openButton).toHaveFocus()
    fireEvent.click(openButton)
    expect(window.location.pathname).toBe('/won/opportunities/41')
    fireEvent.click(screen.getByRole('button', { name: 'Restablecer' }))
    expect(window.location.pathname).toBe('/won')
  })

  it('offers retry after a recoverable initial failure', async () => {
    let fails = true
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = new URL(String(input), 'http://localhost')
        if (url.pathname.endsWith('/filter-options'))
          return json({ products: [], provinces: [], responsible_users: [] })
        if (fails) throw new TypeError('offline')
        if (url.pathname.endsWith('/statistics'))
          return json({ won_count: 0, won_quantity_kg: '0.000' })
        return json({ items: [], next_cursor: null })
      }),
    )
    render(<WonPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('No pudimos cargar')
    fireEvent.click(screen.getByRole('button', { name: 'Cerrar' }))
    fireEvent.change(screen.getByLabelText('Período'), { target: { value: 'all' } })
    fireEvent.click(screen.getByRole('button', { name: 'Aplicar' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('No pudimos cargar')
    fails = false
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    await waitFor(() =>
      expect(screen.getByText('No hay oportunidades ganadas en este período')).toBeVisible(),
    )
  })

  it('shows a compact empty state and resets filters from its action', async () => {
    window.history.replaceState(null, '', '/won?period=all&search=sin-resultados')
    render(<WonPage />)

    expect(await screen.findByText('No hay oportunidades ganadas en este período')).toBeVisible()
    expect(screen.getByText('Probá otro período o ajustá los filtros.')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Restablecer filtros' }))

    expect(window.location.pathname).toBe('/won')
    expect(window.location.search).toBe('')
    expect(screen.getByLabelText('Período')).toHaveValue('month')
  })
})
