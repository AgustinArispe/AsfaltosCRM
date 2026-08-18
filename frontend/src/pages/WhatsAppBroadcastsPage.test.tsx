import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Broadcast, BroadcastTemplate } from '../broadcasts/types'
import { WhatsAppBroadcastsPage } from './WhatsAppBroadcastsPage'

const logout = vi.fn()

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({ token: 'broadcast-token', logout }),
}))

const broadcast: Broadcast = {
  id: 9,
  label: 'Oferta agosto',
  status: 'DRAFT',
  version: 1,
  template_external_id: 'marketing-1',
  template_name: 'oferta_asfalto',
  template_language: 'es_AR',
  template_category: 'MARKETING',
  template_header_type: null,
  template_header_media_required: false,
  header_media_ref: null,
  parameters: [{ name: 'fecha', value: '31/08' }],
  recipient_count: 1,
  outcomes: {
    selected: 1,
    accepted: 0,
    sent: 0,
    delivered: 1,
    read: 0,
    failed: 0,
    unknown: 0,
    skipped: 0,
  },
  validated_at: null,
  confirmed_at: null,
  started_at: null,
  created_at: '2026-08-14T12:00:00Z',
  updated_at: '2026-08-14T12:00:00Z',
}

const template: BroadcastTemplate = {
  external_id: 'marketing-1',
  name: 'oferta_asfalto',
  language: 'es_AR',
  category: 'MARKETING',
  status: 'APPROVED',
  header_type: 'NONE',
  parameter_names: ['fecha'],
  header_media_required: false,
}

function response(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    headers: { 'Content-Type': 'application/json' },
    status: 200,
  })
}

afterEach(() => vi.unstubAllGlobals())

describe('WhatsAppBroadcastsPage', () => {
  it('shows compact history aggregates and progresses a deliberate draft flow', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), 'http://localhost')
      if (url.pathname === '/api/whatsapp/broadcasts' && !init?.method)
        return response({ items: [broadcast], next_cursor: null })
      if (url.pathname === '/api/whatsapp/broadcast-templates') return response([template])
      if (url.pathname === '/api/whatsapp/broadcasts' && init?.method === 'POST')
        return response(broadcast)
      if (url.pathname === '/api/customers')
        return response({ items: [{ id: 2, name: 'Cliente Uno', company: null }], total: 1 })
      return response({ items: [], next_cursor: null })
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<WhatsAppBroadcastsPage />)
    expect(await screen.findByText('Oferta agosto')).toBeInTheDocument()
    expect(screen.getByText('1 entregados')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Nuevo envío masivo' }))
    fireEvent.change(screen.getByLabelText('Nombre operativo'), { target: { value: 'Oferta' } })
    fireEvent.click(await screen.findByRole('radio', { name: /oferta_asfalto/i }))
    fireEvent.change(screen.getByLabelText('fecha'), { target: { value: '01/09' } })
    fireEvent.click(screen.getByRole('button', { name: 'Continuar a clientes' }))

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/api/whatsapp/broadcasts'),
        expect.objectContaining({ method: 'POST' }),
      ),
    )
    expect(
      await screen.findByText('Seleccioná Clientes explícitamente. No se infiere una audiencia.'),
    ).toBeInTheDocument()
  })

  it('presents UNKNOWN as uncertainty and never offers a retry', async () => {
    const unknownRecipient = {
      id: 4,
      customer_id: 2,
      customer_display_name: 'Cliente Uno',
      phone_display: '•••• 0001',
      status: 'UNKNOWN',
      safe_reason: 'No pudimos confirmar la entrega.',
      retry_eligible: false,
      conversation_id: 7,
      latest_attempt_at: null,
      delivered_at: null,
      read_at: null,
      failed_at: null,
    }
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const path = new URL(String(input), 'http://localhost').pathname
        if (path === '/api/whatsapp/broadcasts/9')
          return response({ ...broadcast, status: 'PROCESSING' })
        if (path.endsWith('/recipients'))
          return response({ items: [unknownRecipient], next_cursor: null })
        if (path.endsWith('/audit-events')) return response({ items: [], next_cursor: null })
        return response({ items: [], next_cursor: null })
      }),
    )

    render(<WhatsAppBroadcastsPage broadcastId={9} />)
    expect(await screen.findByText(/Entrega incierta/)).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /Reintentar fallo definitivo/ }),
    ).not.toBeInTheDocument()
  })

  it('validates and confirms only after explicit creation steps', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), 'http://localhost')
      if (url.pathname === '/api/whatsapp/broadcasts' && !init?.method)
        return response({ items: [], next_cursor: null })
      if (url.pathname === '/api/whatsapp/broadcast-templates') return response([template])
      if (url.pathname === '/api/whatsapp/broadcasts' && init?.method === 'POST')
        return response(broadcast)
      if (url.pathname === '/api/customers')
        return response({ items: [{ id: 2, name: 'Cliente Uno', company: null }], total: 1 })
      if (url.pathname === '/api/whatsapp/broadcasts/9/recipients')
        return response({
          broadcast_id: 9,
          version: 2,
          selected_count: 1,
          duplicate_customer_ids: [],
          invalid_customer_ids: [],
          missing_phone_customer_ids: [],
          missing_consent_customer_ids: [],
          replayed: false,
        })
      if (url.pathname === '/api/whatsapp/broadcasts/9/validate')
        return response({
          broadcast_id: 9,
          version: 2,
          valid: true,
          recipient_count: 1,
          validation_token: '11111111-1111-4111-8111-111111111111',
          expires_at: '2026-08-14T13:00:00Z',
          issues: [],
          issue_categories: [],
          eligible_count: 1,
          excluded_count: 0,
        })
      if (url.pathname === '/api/whatsapp/broadcasts/9/confirm')
        return response({ ...broadcast, status: 'CONFIRMED', version: 2 })
      return response({ items: [], next_cursor: null })
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<WhatsAppBroadcastsPage />)

    fireEvent.click(await screen.findByRole('button', { name: 'Nuevo envío masivo' }))
    fireEvent.change(screen.getByLabelText('Nombre operativo'), { target: { value: 'Oferta' } })
    fireEvent.click(await screen.findByRole('radio', { name: /oferta_asfalto/i }))
    fireEvent.change(screen.getByLabelText('fecha'), { target: { value: '01/09' } })
    fireEvent.click(screen.getByRole('button', { name: 'Continuar a clientes' }))
    fireEvent.click(await screen.findByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: 'Revisar elegibilidad' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Validar envío' }))
    expect(await screen.findByText('Resumen final')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar y bloquear envío' }))

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/api/whatsapp/broadcasts/9/confirm'),
        expect.objectContaining({ method: 'POST' }),
      ),
    )
  })

  it('uses bounded recipient operations and explicit processing commands', async () => {
    const failedRecipient = {
      id: 3,
      customer_id: 2,
      customer_display_name: 'Cliente Fallido',
      phone_display: '•••• 0002',
      status: 'FAILED',
      safe_reason: 'El proveedor rechazó el envío.',
      retry_eligible: true,
      conversation_id: null,
      latest_attempt_at: '2026-08-14T12:00:00Z',
      delivered_at: null,
      read_at: null,
      failed_at: '2026-08-14T12:00:00Z',
    }
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input), 'http://localhost')
      if (url.pathname === '/api/whatsapp/broadcasts/9')
        return response({ ...broadcast, status: 'PROCESSING' })
      if (url.pathname === '/api/whatsapp/broadcasts/9/recipients')
        return response({
          items: [failedRecipient],
          next_cursor: url.searchParams.has('cursor') ? null : 'next',
        })
      if (url.pathname === '/api/whatsapp/broadcasts/9/audit-events')
        return response({
          items: [
            {
              id: 1,
              event_type: 'PROCESSED',
              reason_code: null,
              actor_user_id: 2,
              affected_count: 1,
              occurred_at: '2026-08-14T12:00:00Z',
            },
          ],
          next_cursor: url.searchParams.has('cursor') ? null : 'audit-next',
        })
      if (url.pathname === '/api/whatsapp/broadcasts/9/recipients/3/attempts')
        return response({
          items: [
            {
              id: 12,
              attempt_number: 1,
              occurred_at: '2026-08-14T12:00:00Z',
              outcome: 'FAILED',
              safe_reason: 'El proveedor rechazó el envío.',
            },
          ],
          next_cursor: url.searchParams.has('cursor') ? null : 'attempt-next',
        })
      if (url.pathname.endsWith('/process') || url.pathname.endsWith('/retries'))
        return response({
          broadcast_id: 9,
          claimed_count: 1,
          completed_count: 1,
          remaining_count: 0,
          replayed: false,
        })
      return response({ items: [], next_cursor: null })
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<WhatsAppBroadcastsPage broadcastId={9} />)

    fireEvent.click(await screen.findByRole('button', { name: 'Procesar siguiente lote' }))
    fireEvent.change(screen.getByLabelText('Buscar destinatario'), { target: { value: 'Fallido' } })
    fireEvent.change(screen.getByLabelText('Filtrar resultado'), { target: { value: 'FAILED' } })
    fireEvent.click(await screen.findByRole('button', { name: 'Ver intentos' }))
    expect(await screen.findByText(/Intentos de Cliente Fallido/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Cargar más intentos' }))
    fireEvent.click(screen.getByRole('button', { name: 'Cargar más eventos' }))
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar fallo definitivo' }))
    fireEvent.click(screen.getByRole('button', { name: 'Cargar más resultados' }))

    await waitFor(() => {
      expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/retries'))).toBe(true)
      expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/process'))).toBe(true)
    })
    expect(screen.getAllByText('PROCESSED').length).toBeGreaterThan(0)
  })

  it('uploads required header media through the authenticated CRM boundary', async () => {
    const mediaTemplate: BroadcastTemplate = {
      ...template,
      external_id: 'marketing-document',
      header_type: 'DOCUMENT',
      header_media_required: true,
    }
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = new URL(String(input), 'http://localhost').pathname
        if (path === '/api/whatsapp/broadcasts' && !init?.method)
          return response({ items: [], next_cursor: null })
        if (path === '/api/whatsapp/broadcast-templates') return response([mediaTemplate])
        if (path === '/api/whatsapp/media')
          return response({
            media_ref: '22222222-2222-4222-8222-222222222222',
            media_type: 'DOCUMENT',
            mime_type: 'application/pdf',
            filename: 'ficha.pdf',
            size_bytes: 12,
            content_url: '/api/whatsapp/media/22222222-2222-4222-8222-222222222222/content',
          })
        return response({ items: [], next_cursor: null })
      }),
    )
    render(<WhatsAppBroadcastsPage />)
    fireEvent.click(await screen.findByRole('button', { name: 'Nuevo envío masivo' }))
    fireEvent.click(await screen.findByRole('radio', { name: /oferta_asfalto/i }))
    const upload = await screen.findByLabelText(/Encabezado PDF\/documento/)
    fireEvent.change(upload, {
      target: { files: [new File(['pdf'], 'ficha.pdf', { type: 'application/pdf' })] },
    })
    expect(await screen.findByText('ficha.pdf')).toBeInTheDocument()
  })

  it('starts a confirmed broadcast only through its explicit action', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = new URL(String(input), 'http://localhost').pathname
      if (path === '/api/whatsapp/broadcasts/9')
        return response({ ...broadcast, status: 'CONFIRMED' })
      if (path.endsWith('/recipients') || path.endsWith('/audit-events'))
        return response({ items: [], next_cursor: null })
      if (path.endsWith('/start')) return response({ ...broadcast, status: 'PROCESSING' })
      return response({ items: [], next_cursor: null })
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<WhatsAppBroadcastsPage broadcastId={9} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Iniciar procesamiento' }))
    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/start'))).toBe(true),
    )
  })

  it('reopens a Draft with its safe values and allows removing header media', async () => {
    const draftWithMedia: Broadcast = {
      ...broadcast,
      header_media_ref: '22222222-2222-4222-8222-222222222222',
      template_external_id: 'marketing-document',
      template_header_type: 'DOCUMENT',
      template_header_media_required: true,
    }
    const documentTemplate: BroadcastTemplate = {
      ...template,
      external_id: 'marketing-document',
      header_type: 'DOCUMENT',
      header_media_required: true,
    }
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = new URL(String(input), 'http://localhost').pathname
      if (path === '/api/whatsapp/broadcasts/9' && init?.method === 'PUT')
        return response({ ...draftWithMedia, version: 2, header_media_ref: null })
      if (path === '/api/whatsapp/broadcasts/9') return response(draftWithMedia)
      if (path === '/api/whatsapp/broadcast-templates') return response([documentTemplate])
      if (path.endsWith('/recipients') || path.endsWith('/audit-events'))
        return response({ items: [], next_cursor: null })
      return response({ items: [], next_cursor: null })
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<WhatsAppBroadcastsPage broadcastId={9} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Editar borrador' }))
    expect(await screen.findByDisplayValue('Oferta agosto')).toBeInTheDocument()
    await screen.findByRole('radio', { name: /oferta_asfalto/i })
    fireEvent.click(await screen.findByRole('button', { name: 'Quitar medio' }))
    expect(screen.getByRole('button', { name: 'Continuar a clientes' })).toBeDisabled()
  })
})
