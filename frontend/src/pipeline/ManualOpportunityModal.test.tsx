import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { AuthUser } from '../auth/types'
import type { CustomerSummary } from '../customers/types'
import { ManualOpportunityModal } from './ManualOpportunityModal'
import type { OpportunityDetail } from './types'

const supervisor: AuthUser = {
  id: 1,
  full_name: 'Supervisora FAA',
  email: 'supervisora@faa.test',
  role: 'SUPERVISOR',
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const seller: AuthUser = { ...supervisor, id: 2, role: 'VENDEDOR', full_name: 'Vendedor FAA' }

const customer: CustomerSummary = {
  id: 42,
  name: 'Esteban Ríos',
  company: 'Vial Patagonia',
  email: 'esteban@vial.test',
  phone: '+54 9 11 5555-0101',
  province: 'Buenos Aires',
  legendary_historical_override: false,
  is_legendary: false,
  updated_at: '2026-09-10T12:00:00Z',
}

const createdOpportunity: OpportunityDetail = {
  id: 123,
  status: 'NUEVA',
  source: 'REFERIDO',
  current_status_entered_at: '2026-09-10T12:00:00Z',
  customer,
  assigned_user: null,
  products: [],
  created_at: '2026-09-10T12:00:00Z',
  updated_at: '2026-09-10T12:00:00Z',
  history: [],
  loss_reason: null,
  web_intake: null,
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function renderModal(onCreated = vi.fn()) {
  return {
    onCreated,
    ...render(
      <ManualOpportunityModal
        apiSession={{ token: 'token', onUnauthorized: vi.fn() }}
        isOpen
        onClose={vi.fn()}
        onCreated={onCreated}
        returnFocusTo={null}
        user={supervisor}
      />,
    ),
  }
}

describe('ManualOpportunityModal', () => {
  beforeEach(() => {
    vi.stubGlobal('crypto', { randomUUID: vi.fn(() => 'b504fc7b-838f-45b8-92a3-f70e71551ac0') })
  })

  it('selects an existing customer and submits without source or status', async () => {
    let submittedBody: Record<string, unknown> | null = null
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = new URL(String(input), 'http://localhost')
        if (url.pathname === '/api/users') return jsonResponse(200, [supervisor])
        if (url.pathname === '/api/customers') {
          return jsonResponse(200, { items: [customer], page: 1, page_size: 8, total: 1 })
        }
        if (url.pathname === '/api/opportunities/manual') {
          submittedBody = JSON.parse(String(init?.body)) as Record<string, unknown>
          return jsonResponse(201, { created: true, opportunity: createdOpportunity })
        }
        throw new Error(`Unexpected request ${url.pathname}`)
      }),
    )
    const { onCreated } = renderModal()
    const dialog = screen.getByRole('dialog', { name: 'Nueva oportunidad' })

    expect(within(dialog).getByText('Referido / boca a boca')).toBeInTheDocument()
    expect(within(dialog).queryByRole('combobox', { name: 'Origen' })).not.toBeInTheDocument()
    fireEvent.change(within(dialog).getByLabelText('Buscar cliente'), {
      target: { value: 'Vial' },
    })
    fireEvent.click(await within(dialog).findByRole('button', { name: /Vial Patagonia/ }))
    fireEvent.click(within(dialog).getByRole('button', { name: 'Cambiar' }))
    fireEvent.change(within(dialog).getByLabelText('Buscar cliente'), {
      target: { value: 'Vial Patagonia' },
    })
    fireEvent.click(await within(dialog).findByRole('button', { name: /Vial Patagonia/ }))
    fireEvent.click(within(dialog).getByRole('button', { name: 'Crear oportunidad' }))

    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(createdOpportunity))
    expect(submittedBody).toMatchObject({
      assigned_user_id: null,
      customer: { kind: 'existing', customer_id: 42 },
    })
    expect(submittedBody).not.toHaveProperty('source')
    expect(submittedBody).not.toHaveProperty('status')
  })

  it('creates a new customer and offers deliberate reuse on an exact match', async () => {
    let attempts = 0
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = new URL(String(input), 'http://localhost')
        if (url.pathname === '/api/users') return jsonResponse(200, [supervisor])
        if (url.pathname === '/api/opportunities/manual') {
          attempts += 1
          return jsonResponse(409, {
            detail: { code: 'MANUAL_CUSTOMER_MATCH_EXISTS', customer },
          })
        }
        throw new Error(`Unexpected request ${url.pathname}`)
      }),
    )
    renderModal()
    const dialog = screen.getByRole('dialog', { name: 'Nueva oportunidad' })

    fireEvent.click(within(dialog).getByRole('button', { name: 'Cliente nuevo' }))
    fireEvent.click(within(dialog).getByRole('button', { name: 'Cliente existente' }))
    fireEvent.click(within(dialog).getByRole('button', { name: 'Cliente nuevo' }))
    fireEvent.change(within(dialog).getByLabelText('Nombre *'), {
      target: { value: 'Esteban Ríos' },
    })
    fireEvent.change(within(dialog).getByLabelText('Email'), {
      target: { value: 'esteban@vial.test' },
    })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Crear oportunidad' }))

    expect(
      await within(dialog).findByText('Ya existe un cliente con ese email o teléfono.'),
    ).toBeInTheDocument()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Usar cliente existente' }))
    expect(within(dialog).getByText('Vial Patagonia')).toBeInTheDocument()
    expect(within(dialog).getByText(/esteban@vial.test/)).toBeInTheDocument()
    expect(attempts).toBe(1)
  })

  it('keeps one command across a retry and sends all supported new-customer fields', async () => {
    const submittedBodies: Record<string, unknown>[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = new URL(String(input), 'http://localhost')
        if (url.pathname === '/api/users') {
          return jsonResponse(200, [supervisor, { ...seller, is_active: false }])
        }
        if (url.pathname === '/api/opportunities/manual') {
          submittedBodies.push(JSON.parse(String(init?.body)) as Record<string, unknown>)
          if (submittedBodies.length === 1) throw new TypeError('network unavailable')
          return jsonResponse(201, { created: true, opportunity: createdOpportunity })
        }
        throw new Error(`Unexpected request ${url.pathname}`)
      }),
    )
    const onClose = vi.fn()
    const onCreated = vi.fn()
    render(
      <ManualOpportunityModal
        apiSession={{ token: 'token', onUnauthorized: vi.fn() }}
        isOpen
        onClose={onClose}
        onCreated={onCreated}
        returnFocusTo={null}
        user={supervisor}
      />,
    )
    const dialog = screen.getByRole('dialog', { name: 'Nueva oportunidad' })

    fireEvent.click(within(dialog).getByRole('button', { name: 'Cliente nuevo' }))
    fireEvent.change(within(dialog).getByLabelText('Nombre *'), { target: { value: ' María ' } })
    fireEvent.change(within(dialog).getByLabelText('Empresa'), { target: { value: ' Vial Sur ' } })
    fireEvent.change(within(dialog).getByLabelText('Teléfono'), { target: { value: ' 1234567 ' } })
    fireEvent.change(within(dialog).getByLabelText('Email'), {
      target: { value: ' maria@example.com ' },
    })
    fireEvent.change(within(dialog).getByLabelText('Provincia'), { target: { value: ' Salta ' } })
    expect(
      await within(dialog).findByRole('option', { name: 'Supervisora FAA' }),
    ).toBeInTheDocument()
    fireEvent.change(within(dialog).getByLabelText('Responsable'), { target: { value: '1' } })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Crear oportunidad' }))

    expect(
      await within(dialog).findByText(
        'No pudimos crear la oportunidad. Conservamos los datos para que vuelvas a intentar.',
      ),
    ).toBeInTheDocument()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Crear oportunidad' }))
    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(createdOpportunity))
    expect(submittedBodies[0]?.command_id).toBe(submittedBodies[1]?.command_id)
    expect(submittedBodies[1]).toMatchObject({
      assigned_user_id: 1,
      customer: {
        kind: 'new',
        name: 'María',
        company: 'Vial Sur',
        phone: '1234567',
        email: 'maria@example.com',
        province: 'Salta',
      },
    })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Cancelar' }))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('shows validation and lookup errors without losing the manual draft', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = new URL(String(input), 'http://localhost')
        if (url.pathname === '/api/users') throw new Error('users unavailable')
        if (url.pathname === '/api/customers') throw new Error('customers unavailable')
        throw new Error(`Unexpected request ${url.pathname}`)
      }),
    )
    renderModal()
    const dialog = screen.getByRole('dialog', { name: 'Nueva oportunidad' })

    fireEvent.change(within(dialog).getByLabelText('Buscar cliente'), { target: { value: 'FAA' } })
    expect(
      await within(dialog).findByText('No pudimos buscar clientes. Intentá nuevamente.'),
    ).toBeInTheDocument()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Cliente nuevo' }))
    fireEvent.click(within(dialog).getByRole('button', { name: 'Crear oportunidad' }))
    expect(within(dialog).getByText('Ingresá el nombre del cliente.')).toBeInTheDocument()
    fireEvent.change(within(dialog).getByLabelText('Nombre *'), { target: { value: 'Cliente' } })
    fireEvent.change(within(dialog).getByLabelText('Email'), { target: { value: 'inválido' } })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Crear oportunidad' }))
    expect(within(dialog).getByText('Ingresá un email válido.')).toBeInTheDocument()
    expect(
      await within(dialog).findByText(
        'No pudimos cargar responsables. Podés crearla sin responsable.',
      ),
    ).toBeInTheDocument()
  })

  it('keeps seller creation unassigned and exposes no user selector', () => {
    vi.stubGlobal('fetch', vi.fn())
    render(
      <ManualOpportunityModal
        apiSession={{ token: 'token', onUnauthorized: vi.fn() }}
        isOpen
        onClose={vi.fn()}
        onCreated={vi.fn()}
        returnFocusTo={null}
        user={seller}
      />,
    )

    expect(screen.queryByRole('combobox', { name: 'Responsable' })).not.toBeInTheDocument()
    expect(screen.getByText('Sin responsable')).toBeInTheDocument()
  })
})
