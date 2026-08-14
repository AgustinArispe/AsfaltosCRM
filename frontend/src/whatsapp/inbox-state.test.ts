import { describe, expect, it } from 'vitest'

import {
  conversationActivityLabel,
  conversationMatchesFilters,
  filterConversations,
  upsertConversations,
  upsertMessages,
} from './inbox-state'
import type { WhatsAppConversationSummary, WhatsAppMessage } from './types'

function conversation(
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
      name: `Cliente ${id}`,
      company: `Empresa ${id}`,
      phone: null,
      province: null,
      is_available: true,
    },
    active_opportunity: null,
    opportunity_suggestions: [],
    last_message_at: `2026-08-10T12:0${id}:00Z`,
    last_inbound_at: `2026-08-10T12:0${id}:00Z`,
    last_outbound_at: null,
    unread_count: 0,
    waiting_for_response: false,
    waiting_since_at: null,
    can_send_freeform: true,
    window_expires_at: '2026-08-11T12:00:00Z',
    template_required: false,
    reason: null,
    updated_at: `2026-08-10T12:0${id}:00Z`,
    resource_updated_at: `2026-08-10T12:0${id}:00Z`,
    ...overrides,
  }
}

function message(id: number, overrides: Partial<WhatsAppMessage> = {}): WhatsAppMessage {
  return {
    id,
    conversation_id: 1,
    external_message_id: `wamid.${id}`,
    client_generated_id: null,
    direction: 'INBOUND',
    message_type: 'TEXT',
    origin: 'HUMAN',
    body: `Mensaje ${id}`,
    template_name: null,
    template_language: null,
    sent_by: null,
    retry_of_message_id: null,
    is_retry: false,
    message_at: `2026-08-10T12:0${id}:00Z`,
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
    created_at: `2026-08-10T12:0${id}:00Z`,
    updated_at: `2026-08-10T12:0${id}:00Z`,
    resource_updated_at: `2026-08-10T12:0${id}:00Z`,
    ...overrides,
  }
}

describe('WhatsApp Inbox state reconciliation', () => {
  it('keeps the backend inbox order with deterministic ID ties', () => {
    const items = upsertConversations(
      [],
      [
        conversation(1, { unread_count: 2 }),
        conversation(2, { waiting_for_response: true }),
        conversation(3, {
          last_message_at: '2026-08-10T12:01:00Z',
          unread_count: 2,
        }),
      ],
    )

    expect(items.map((item) => item.id)).toEqual([2, 3, 1])
  })

  it('applies combined waiting, unread, text and normalized-phone filters', () => {
    const waiting = conversation(1, {
      waiting_for_response: true,
      unread_count: 3,
    })
    const attended = conversation(2)

    expect(
      filterConversations([waiting, attended], {
        waitingOnly: true,
        unreadOnly: true,
        search: 'Empresa 1',
      }),
    ).toEqual([waiting])
    expect(
      conversationMatchesFilters(waiting, {
        waitingOnly: false,
        unreadOnly: false,
        search: '1155550001',
      }),
    ).toBe(true)
  })

  it('does not replace a newer conversation projection with an older poll item', () => {
    const newer = conversation(1, {
      unread_count: 0,
      resource_updated_at: '2026-08-10T15:00:00Z',
    })
    const stale = conversation(1, {
      unread_count: 4,
      resource_updated_at: '2026-08-10T14:00:00Z',
    })

    expect(upsertConversations([newer], [stale])[0]?.unread_count).toBe(0)
  })

  it('upserts messages by ID, preserves chronological order and rejects status downgrade', () => {
    const read = message(2, {
      direction: 'OUTBOUND',
      resource_updated_at: '2026-08-10T16:00:00Z',
      status: {
        ...message(2).status,
        dispatch_state: 'ACCEPTED',
        provider_state: 'READ',
      },
    })
    const staleSent = message(2, {
      direction: 'OUTBOUND',
      resource_updated_at: '2026-08-10T15:00:00Z',
      status: {
        ...message(2).status,
        dispatch_state: 'ACCEPTED',
        provider_state: 'SENT',
      },
    })

    const result = upsertMessages([read], [message(1), staleSent])
    expect(result.map((item) => item.id)).toEqual([1, 2])
    expect(result[1]?.status.provider_state).toBe('READ')
  })

  it('derives only safe activity summaries from conversation projections', () => {
    expect(conversationActivityLabel(conversation(1, { last_message_at: null }))).toBe(
      'Sin mensajes',
    )
    expect(
      conversationActivityLabel(
        conversation(1, { resolution_status: 'NEEDS_REVIEW', customer: null }),
      ),
    ).toBe('Identidad pendiente de revisión')
  })
})
