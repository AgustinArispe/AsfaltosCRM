import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { WhatsAppInboxPage } from './WhatsAppInboxPage'
import type { CustomerDetail } from '../customers/types'
import type { OpportunityDetail } from '../pipeline/types'
import type {
  WhatsAppConversationDetail,
  WhatsAppConversationSummary,
  WhatsAppMessage,
  WhatsAppMessageType,
} from '../whatsapp/types'

const authState = vi.hoisted(() => ({ logout: vi.fn() }))

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({ token: 'whatsapp-token', logout: authState.logout }),
}))

const customerDetail: CustomerDetail = {
  id: 11,
  name: 'Cliente Uno',
  company: 'Constructora Uno',
  email: 'compras@uno.test',
  phone: '+54 11 5555-0001',
  province: 'Buenos Aires',
  legendary_historical_override: false,
  created_at: '2026-08-01T12:00:00Z',
}

const opportunityDetail: OpportunityDetail = {
  id: 77,
  status: 'COTIZADA',
  source: 'WHATSAPP',
  current_status_entered_at: '2026-08-09T12:00:00Z',
  customer: customerDetail,
  assigned_user: null,
  products: [
    {
      product: { id: 5, name: 'SuperPhalt', is_active: true },
      quantity_kg: '2500.000',
    },
  ],
  created_at: '2026-08-01T12:00:00Z',
  history: [],
  loss_reason: null,
  updated_at: '2026-08-09T12:00:00Z',
}

function summary(
  id: number,
  overrides: Partial<WhatsAppConversationSummary> = {},
): WhatsAppConversationSummary {
  return {
    id,
    external_phone: `+54 11 5555-000${id}`,
    display_name: `Contacto ${id}`,
    resolution_status: 'RESOLVED',
    customer: {
      id: id + 10,
      name: id === 1 ? 'Cliente Uno' : `Cliente ${id}`,
      company: id === 1 ? 'Constructora Uno' : `Empresa ${id}`,
      phone: `+54 11 5555-000${id}`,
      province: 'Buenos Aires',
      is_available: true,
    },
    active_opportunity:
      id === 1
        ? {
            id: 77,
            status: 'COTIZADA',
            source: 'WHATSAPP',
            created_at: '2026-08-01T12:00:00Z',
            linked_at: '2026-08-01T12:00:00Z',
            is_open: true,
            is_available: true,
          }
        : null,
    opportunity_suggestions: [],
    last_message_at: `2026-08-10T15:0${id}:00Z`,
    last_inbound_at: `2026-08-10T15:0${id}:00Z`,
    last_outbound_at: null,
    unread_count: id === 1 ? 2 : 0,
    waiting_for_response: id === 1,
    waiting_since_at: id === 1 ? '2026-08-10T15:01:00Z' : null,
    can_send_freeform: true,
    window_expires_at: '2026-08-11T15:01:00Z',
    template_required: false,
    reason: null,
    updated_at: `2026-08-10T15:0${id}:00Z`,
    resource_updated_at: `2026-08-10T15:0${id}:00Z`,
    ...overrides,
  }
}

function detail(
  overrides: Partial<WhatsAppConversationDetail> = {},
): WhatsAppConversationDetail {
  return {
    ...summary(1),
    opportunity_links: [
      {
        id: 10,
        opportunity: summary(1).active_opportunity!,
        linked_at: '2026-08-01T12:00:00Z',
        unlinked_at: null,
        linked_by: { id: 2, full_name: 'Vendedor FAA', role: 'VENDEDOR' },
        link_source: 'MANUAL',
        is_active: true,
        is_actionable: true,
      },
    ],
    created_at: '2026-08-01T12:00:00Z',
    ...overrides,
  }
}

function message(
  id: number,
  overrides: Partial<WhatsAppMessage> = {},
): WhatsAppMessage {
  const minute = String(id % 60).padStart(2, '0')
  return {
    id,
    conversation_id: 1,
    external_message_id: `wamid.${id}`,
    client_generated_id: null,
    direction: 'INBOUND',
    message_type: 'TEXT',
    body: id === 1 ? 'Necesito una cotización' : `Mensaje ${id}`,
    sent_by: null,
    retry_of_message_id: null,
    is_retry: false,
    message_at: `2026-08-10T15:${minute}:00Z`,
    attachment: null,
    status: {
      dispatch_state: null,
      provider_state: 'RECEIVED',
      accepted_at: null,
      sent_at: null,
      delivered_at: null,
      read_at: null,
      failed_at: null,
      error_code: null,
      error_message: null,
    },
    created_at: `2026-08-10T15:${minute}:00Z`,
    updated_at: `2026-08-10T15:${minute}:00Z`,
    resource_updated_at: `2026-08-10T15:${minute}:00Z`,
    ...overrides,
  }
}

function outboundMessage(
  id: number,
  type: WhatsAppMessageType = 'TEXT',
): WhatsAppMessage {
  const minute = String(id % 60).padStart(2, '0')
  return message(id, {
    external_message_id: `wamid.out.${id}`,
    client_generated_id: '11111111-1111-4111-8111-111111111111',
    direction: 'OUTBOUND',
    message_type: type,
    body: type === 'TEXT' ? 'Respuesta del equipo' : 'Archivo adjunto',
    sent_by: { id: 2, full_name: 'Vendedor FAA', role: 'VENDEDOR' },
    attachment:
      type === 'TEXT'
        ? null
        : {
            id: 90 + id,
            media_type: type,
            mime_type: type === 'IMAGE' ? 'image/png' : 'application/pdf',
            filename: type === 'IMAGE' ? 'muestra.png' : 'ficha.pdf',
            size_bytes: 2400,
            is_available: true,
            content_url: `/api/whatsapp/attachments/${90 + id}/content`,
          },
    status: {
      ...message(id).status,
      dispatch_state: 'ACCEPTED',
      provider_state: 'DELIVERED',
      accepted_at: `2026-08-10T15:${minute}:00Z`,
      delivered_at: `2026-08-10T15:${minute}:30Z`,
    },
  })
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

type MockApiOptions = {
  conversations?: WhatsAppConversationSummary[]
  conversationDetail?: WhatsAppConversationDetail
  messages?: WhatsAppMessage[]
  initialFailure?: boolean
  send?: (
    payload: Record<string, unknown>,
    call: number,
  ) => Response | Promise<Response>
  conversationChanges?: WhatsAppConversationSummary[][]
  olderMessages?: WhatsAppMessage[]
}

function mockInboxApi({
  conversations = [summary(1), summary(2)],
  conversationDetail = detail(),
  messages = [message(1), outboundMessage(2)],
  initialFailure = false,
  send,
  conversationChanges = [[]],
  olderMessages = [],
}: MockApiOptions = {}) {
  let shouldFailInitial = initialFailure
  let sendCalls = 0
  let changeCalls = 0
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = new URL(String(input), 'http://localhost')
      const method = init?.method ?? 'GET'
      if (url.pathname === '/api/whatsapp/conversations' && method === 'GET') {
        if (shouldFailInitial) {
          shouldFailInitial = false
          throw new TypeError('network unavailable')
        }
        return jsonResponse(200, {
          items: conversations,
          next_page_cursor: null,
          sync_cursor: 'conversation-cursor-1',
        })
      }
      if (url.pathname === '/api/whatsapp/conversations/changes') {
        const items = conversationChanges[Math.min(changeCalls, conversationChanges.length - 1)] ?? []
        changeCalls += 1
        return jsonResponse(200, {
          items,
          next_cursor: `conversation-cursor-${changeCalls + 1}`,
          has_more: changeCalls < conversationChanges.length,
        })
      }
      if (url.pathname === '/api/whatsapp/conversations/1' && method === 'GET') {
        return jsonResponse(200, conversationDetail)
      }
      if (
        url.pathname === '/api/whatsapp/conversations/1/messages' &&
        method === 'GET'
      ) {
        const isOlderPage = url.searchParams.has('before_cursor')
        return jsonResponse(200, {
          items: isOlderPage ? olderMessages : messages,
          next_before_cursor:
            !isOlderPage && olderMessages.length > 0 ? 'older-cursor-1' : null,
          sync_cursor: 'message-cursor-1',
        })
      }
      if (url.pathname === '/api/whatsapp/conversations/1/messages/changes') {
        return jsonResponse(200, {
          items: [],
          next_cursor: 'message-cursor-2',
          has_more: false,
        })
      }
      if (url.pathname === '/api/whatsapp/conversations/1/read') {
        return jsonResponse(200, { ...conversationDetail, unread_count: 0 })
      }
      if (url.pathname === '/api/customers/11') {
        return jsonResponse(200, customerDetail)
      }
      if (url.pathname === '/api/opportunities/77') {
        return jsonResponse(200, opportunityDetail)
      }
      if (
        url.pathname === '/api/whatsapp/conversations/1/messages' &&
        method === 'POST'
      ) {
        sendCalls += 1
        const payload = JSON.parse(String(init?.body)) as Record<string, unknown>
        if (send) return send(payload, sendCalls)
        return jsonResponse(201, {
          message: outboundMessage(20, String(payload.message_type) as WhatsAppMessageType),
          can_send_freeform: true,
          window_expires_at: '2026-08-11T15:01:00Z',
          template_required: false,
          reason: null,
        })
      }
      if (url.pathname === '/api/whatsapp/media' && method === 'POST') {
        return jsonResponse(201, {
          media_ref: '22222222-2222-4222-8222-222222222222',
          media_type: 'DOCUMENT',
          mime_type: 'application/pdf',
          filename: 'ficha.pdf',
          size_bytes: 8,
          content_url: '/api/whatsapp/media/22222222-2222-4222-8222-222222222222/content',
        })
      }
      if (url.pathname.match(/^\/api\/whatsapp\/(attachments|media)\//)) {
        return new Response(new Blob(['stored media'], { type: 'application/pdf' }), {
          status: 200,
          headers: { 'Content-Type': 'application/pdf' },
        })
      }
      if (
        url.pathname === '/api/whatsapp/conversations/1/opportunity-link' &&
        method === 'PUT'
      ) {
        const payload = JSON.parse(String(init?.body)) as { opportunity_id: number }
        const opportunity = conversationDetail.opportunity_suggestions.find(
          (item) => item.id === payload.opportunity_id,
        )!
        return jsonResponse(200, {
          ...conversationDetail,
          active_opportunity: opportunity,
          opportunity_suggestions: [],
          opportunity_links: [
            ...conversationDetail.opportunity_links.map((link) => ({
              ...link,
              is_active: false,
              unlinked_at: '2026-08-10T16:00:00Z',
            })),
            {
              id: 99,
              opportunity,
              linked_at: '2026-08-10T16:00:00Z',
              unlinked_at: null,
              linked_by: { id: 2, full_name: 'Vendedor FAA', role: 'VENDEDOR' },
              link_source: 'MANUAL',
              is_active: true,
              is_actionable: true,
            },
          ],
        })
      }
      if (
        url.pathname === '/api/whatsapp/conversations/1/opportunity-link' &&
        method === 'DELETE'
      ) {
        return jsonResponse(200, {
          ...conversationDetail,
          active_opportunity: null,
          opportunity_links: conversationDetail.opportunity_links.map((link) => ({
            ...link,
            is_active: false,
            unlinked_at: '2026-08-10T16:00:00Z',
          })),
        })
      }
      throw new Error(`Unexpected request: ${method} ${url.pathname}`)
    },
  )
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

async function openConversation() {
  expect(
    await screen.findByRole('heading', { name: 'Cliente Uno' }),
  ).toBeInTheDocument()
  await screen.findByText('Necesito una cotización')
}

describe('WhatsAppInboxPage', () => {
  beforeEach(() => {
    authState.logout.mockReset()
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      value: vi.fn(() => 'blob:http://localhost/media'),
    })
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      value: vi.fn(),
    })
  })

  it('loads the prioritized Inbox, marks global read and enriches only selected CRM context', async () => {
    const fetchMock = mockInboxApi()
    render(<WhatsAppInboxPage />)
    await openConversation()

    expect(screen.getByRole('heading', { name: 'Conversaciones' })).toBeInTheDocument()
    expect(screen.getByText('Respuesta pendiente.')).toBeInTheDocument()
    expect(screen.getByText('Entregado')).toBeInTheDocument()
    expect(await screen.findByText('compras@uno.test')).toBeInTheDocument()
    expect(screen.getByText('SuperPhalt')).toBeInTheDocument()
    expect(screen.getByText('2.500 kg')).toBeInTheDocument()

    const readCall = fetchMock.mock.calls.find(([input, init]) =>
      String(input).endsWith('/api/whatsapp/conversations/1/read') &&
      init?.method === 'POST',
    )
    expect(readCall).toBeDefined()
    expect(new Headers(readCall?.[1]?.headers).get('Authorization')).toBe(
      'Bearer whatsapp-token',
    )
    expect(screen.queryByLabelText('2 mensajes sin leer')).not.toBeInTheDocument()
    expect(screen.getByText('Respuesta pendiente.')).toBeInTheDocument()
  })

  it('retries a failed initial load and shows distinct filtered empty results', async () => {
    mockInboxApi({ initialFailure: true })
    render(<WhatsAppInboxPage />)

    expect(
      await screen.findByText('No pudimos cargar la bandeja'),
    ).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    await openConversation()

    fireEvent.change(screen.getByRole('searchbox', { name: 'Buscar conversaciones' }), {
      target: { value: 'cliente inexistente' },
    })
    expect(
      await screen.findByText('No hay conversaciones para mostrar'),
    ).toBeInTheDocument()
  })

  it('combines waiting and unread filters in a fresh backend snapshot', async () => {
    const fetchMock = mockInboxApi()
    render(<WhatsAppInboxPage />)
    await openConversation()

    fireEvent.click(screen.getByRole('button', { name: 'Esperando' }))
    fireEvent.click(screen.getByRole('button', { name: 'No leídas' }))
    await waitFor(() => {
      const filteredRequest = fetchMock.mock.calls
        .map(([input]) => new URL(String(input), 'http://localhost'))
        .find(
          (url) =>
            url.pathname === '/api/whatsapp/conversations' &&
            url.searchParams.get('waiting_only') === 'true' &&
            url.searchParams.get('unread_only') === 'true',
        )
      expect(filteredRequest).toBeDefined()
    })
    expect(screen.getByRole('button', { name: 'Esperando' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(screen.getByRole('button', { name: 'No leídas' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })

  it('pages older history without duplicating the active message log', async () => {
    mockInboxApi({ olderMessages: [message(0, { body: 'Mensaje anterior' })] })
    render(<WhatsAppInboxPage />)
    await openConversation()

    fireEvent.click(
      screen.getByRole('button', { name: 'Cargar mensajes anteriores' }),
    )
    expect(await screen.findByText('Mensaje anterior')).toBeInTheDocument()
    expect(screen.getAllByText('Necesito una cotización')).toHaveLength(1)
    expect(screen.getAllByRole('log')).toHaveLength(1)
  })

  it('sends text with one client ID and reuses it after a transport failure', async () => {
    const sentPayloads: Record<string, unknown>[] = []
    mockInboxApi({
      send: (payload, call) => {
        sentPayloads.push(payload)
        if (call === 1) throw new TypeError('network unavailable')
        return jsonResponse(201, {
          message: outboundMessage(20),
          can_send_freeform: true,
          window_expires_at: '2026-08-11T15:01:00Z',
          template_required: false,
          reason: null,
        })
      },
    })
    render(<WhatsAppInboxPage />)
    await openConversation()

    const composer = screen.getByLabelText('Mensaje')
    fireEvent.change(composer, { target: { value: 'Enseguida te respondemos' } })
    fireEvent.keyDown(composer, { key: 'Enter', shiftKey: true })
    expect(sentPayloads).toHaveLength(0)
    fireEvent.keyDown(composer, { key: 'Enter' })

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No pudimos enviar el mensaje',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar mismo envío' }))

    await screen.findByText('Respuesta del equipo')
    expect(sentPayloads).toHaveLength(2)
    expect(sentPayloads[0]?.client_generated_id).toBe(
      sentPayloads[1]?.client_generated_id,
    )
    expect(sentPayloads[1]).toMatchObject({
      message_type: 'TEXT',
      body: 'Enseguida te respondemos',
    })
    expect(composer).toHaveValue('')
  })

  it.each([
    ['application/pdf', 'ficha.pdf', 'DOCUMENT'],
    ['image/png', 'muestra.png', 'IMAGE'],
  ] as const)('uploads and sends %s without base64 or provider URLs', async (mime, filename, expectedType) => {
    const fetchMock = mockInboxApi()
    render(<WhatsAppInboxPage />)
    await openConversation()

    const file = new File(['content'], filename, { type: mime })
    fireEvent.change(screen.getByLabelText('Adjuntar imagen o PDF'), {
      target: { files: [file] },
    })
    fireEvent.change(screen.getByLabelText('Mensaje'), {
      target: { value: 'Adjunto documentación' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Enviar' }))

    await waitFor(() => {
      const sendCall = fetchMock.mock.calls.find(([input, init]) =>
        String(input).endsWith('/api/whatsapp/conversations/1/messages') &&
        init?.method === 'POST',
      )
      expect(sendCall).toBeDefined()
    })
    const uploadCall = fetchMock.mock.calls.find(([input]) =>
      String(input).endsWith('/api/whatsapp/media'),
    )
    expect(uploadCall?.[1]?.body).toBeInstanceOf(FormData)
    const metadata = (uploadCall?.[1]?.body as FormData).get('metadata')
    expect(metadata).toBe(JSON.stringify({ media_type: expectedType }))

    const sendCall = fetchMock.mock.calls.find(([input, init]) =>
      String(input).endsWith('/api/whatsapp/conversations/1/messages') &&
      init?.method === 'POST',
    )
    const payload = JSON.parse(String(sendCall?.[1]?.body)) as Record<string, unknown>
    expect(payload).toMatchObject({
      message_type: expectedType,
      media_ref: '22222222-2222-4222-8222-222222222222',
      caption: 'Adjunto documentación',
    })
    expect(String(sendCall?.[1]?.body)).not.toContain('content')
    expect(String(sendCall?.[1]?.body)).not.toContain('graph.facebook')
  })

  it('blocks freeform composition with backend template-required evidence', async () => {
    mockInboxApi({
      conversationDetail: detail({
        can_send_freeform: false,
        template_required: true,
        reason: 'APPROVED_TEMPLATE_REQUIRED',
        window_expires_at: '2026-08-09T15:01:00Z',
      }),
    })
    render(<WhatsAppInboxPage />)
    await openConversation()

    expect(screen.getByLabelText('Mensaje')).toBeDisabled()
    expect(
      screen.getAllByText(/Se requiere un template aprobado/).length,
    ).toBeGreaterThan(0)
    expect(screen.queryByRole('button', { name: /enviar template/i })).not.toBeInTheDocument()
  })

  it('replaces and unlinks opportunities through explicit accessible confirmations', async () => {
    const suggested = {
      id: 78,
      status: 'NUEVA' as const,
      source: 'WHATSAPP' as const,
      created_at: '2026-08-10T12:00:00Z',
      linked_at: null,
      is_open: true,
      is_available: true,
    }
    const conversationDetail = detail({ opportunity_suggestions: [suggested] })
    const fetchMock = mockInboxApi({ conversationDetail })
    render(<WhatsAppInboxPage />)
    await openConversation()

    fireEvent.click(screen.getByRole('button', { name: 'Ver contexto CRM' }))
    const drawer = await screen.findByRole('dialog', { name: 'Contexto CRM' })
    fireEvent.click(within(drawer).getByRole('button', { name: 'Reemplazar' }))
    const confirmation = await screen.findByRole('dialog', {
      name: 'Reemplazar oportunidad activa',
    })
    fireEvent.click(within(confirmation).getByRole('button', { name: 'Confirmar' }))

    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(([input, init]) =>
          String(input).endsWith('/opportunity-link') && init?.method === 'PUT',
        ),
      ).toBe(true),
    )
    expect(within(drawer).getByText('El historial conserva 2 vínculos.')).toBeInTheDocument()

    fireEvent.click(within(drawer).getByRole('button', { name: 'Desvincular' }))
    const unlinkConfirmation = await screen.findByRole('dialog', {
      name: 'Desvincular oportunidad',
    })
    fireEvent.click(within(unlinkConfirmation).getByRole('button', { name: 'Confirmar' }))
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(([input, init]) =>
          String(input).endsWith('/opportunity-link') && init?.method === 'DELETE',
        ),
      ).toBe(true),
    )
  })

  it('renders authenticated image/document content and durable status evidence safely', async () => {
    const failed = outboundMessage(4)
    failed.status = {
      ...failed.status,
      dispatch_state: 'UNKNOWN',
      provider_state: null,
      error_message: 'Safe provider uncertainty',
    }
    const fetchMock = mockInboxApi({
      messages: [message(1), outboundMessage(2, 'IMAGE'), outboundMessage(3, 'DOCUMENT'), failed],
    })
    render(<WhatsAppInboxPage />)
    await openConversation()

    expect(await screen.findByAltText('Imagen muestra.png')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /ficha.pdf/ })).toBeInTheDocument()
    expect(screen.getByText('Aceptación sin confirmar')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reenviar explícitamente' })).toBeInTheDocument()
    const mediaCalls = fetchMock.mock.calls.filter(([input]) =>
      String(input).includes('/api/whatsapp/attachments/'),
    )
    expect(mediaCalls).toHaveLength(2)
    for (const call of mediaCalls) {
      expect(new Headers(call[1]?.headers).get('Authorization')).toBe(
        'Bearer whatsapp-token',
      )
    }
    expect(document.body).not.toHaveTextContent('storage_key')
    expect(document.body).not.toHaveTextContent('graph.facebook.com')
  })

  it('drains incremental changes, reorders rows and keeps the active selection stable', async () => {
    const fetchMock = mockInboxApi({
      conversationChanges: [
        [summary(2, { waiting_for_response: true, unread_count: 5, resource_updated_at: '2026-08-10T16:00:00Z' })],
        [],
      ],
    })
    render(<WhatsAppInboxPage />)
    await openConversation()

    act(() => window.dispatchEvent(new Event('focus')))
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.filter(([input]) =>
          String(input).includes('/api/whatsapp/conversations/changes'),
        ),
      ).toHaveLength(2),
    )
    expect(screen.getByRole('heading', { name: 'Cliente Uno' })).toBeInTheDocument()
    const rows = screen.getAllByRole('button').filter((button) =>
      button.textContent?.includes('Cliente 2') || button.textContent?.includes('Cliente Uno'),
    )
    expect(rows[0]).toHaveTextContent('Cliente 2')
    expect(
      fetchMock.mock.calls.filter(([input]) => {
        const url = new URL(String(input), 'http://localhost')
        return url.pathname === '/api/whatsapp/conversations'
      }),
    ).toHaveLength(1)
  })

  it('pauses send while offline and performs cursor resync on reconnect', async () => {
    const onlineSpy = vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(false)
    const fetchMock = mockInboxApi()
    render(<WhatsAppInboxPage />)
    await openConversation()

    expect(screen.getByText(/Sin conexión. Conservamos lo cargado/)).toBeInTheDocument()
    expect(screen.getByLabelText('Mensaje')).toBeDisabled()

    onlineSpy.mockReturnValue(true)
    act(() => window.dispatchEvent(new Event('online')))
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(([input]) =>
          String(input).includes('/api/whatsapp/conversations/changes'),
        ),
      ).toBe(true),
    )
    expect(screen.queryByText(/Sin conexión. Conservamos lo cargado/)).not.toBeInTheDocument()
  })
})
