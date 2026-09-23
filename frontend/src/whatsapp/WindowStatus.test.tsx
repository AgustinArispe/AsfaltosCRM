import { act, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { WhatsAppConversationSummary } from './types'
import { conversationWindowStatus, useConversationWindowStatus } from './WindowStatus'

const now = new Date('2026-09-23T12:00:00Z').getTime()

function conversation(
  overrides: Partial<WhatsAppConversationSummary> = {},
): WhatsAppConversationSummary {
  return {
    id: 1,
    external_phone: '+54 11 5555-0001',
    display_name: 'Cliente Uno',
    resolution_status: 'RESOLVED',
    customer: {
      id: 2,
      name: 'Cliente Uno',
      company: null,
      phone: '+54 11 5555-0001',
      province: null,
      is_available: true,
    },
    active_opportunity: null,
    opportunity_suggestions: [],
    last_message_at: '2026-09-23T12:00:00Z',
    last_inbound_at: '2026-09-23T12:00:00Z',
    last_outbound_at: null,
    unread_count: 0,
    waiting_for_response: false,
    waiting_since_at: null,
    can_send_freeform: true,
    window_expires_at: new Date(now + 4 * 60 * 60 * 1000).toISOString(),
    template_required: false,
    reason: null,
    updated_at: '2026-09-23T12:00:00Z',
    resource_updated_at: '2026-09-23T12:00:00Z',
    ...overrides,
  }
}

function StatusProbe({ value }: { value: WhatsAppConversationSummary }) {
  const status = useConversationWindowStatus(value)
  return <output>{status?.label}</output>
}

describe('conversationWindowStatus', () => {
  afterEach(() => vi.useRealTimers())

  it('distinguishes open, closing-soon and closed windows with a compact countdown', () => {
    expect(conversationWindowStatus(conversation(), now)).toMatchObject({
      kind: 'OPEN',
      label: 'Ventana abierta · quedan 4 h',
    })
    expect(
      conversationWindowStatus(
        conversation({ window_expires_at: new Date(now + 102 * 60 * 1000).toISOString() }),
        now,
      ),
    ).toMatchObject({ kind: 'CLOSING_SOON', label: 'Ventana por cerrar · quedan 1 h 42 min' })
    expect(conversationWindowStatus(conversation({ can_send_freeform: false }), now)).toMatchObject(
      { kind: 'CLOSED', label: 'Ventana cerrada' },
    )
  })

  it('updates at the warning threshold without reloading the page', () => {
    vi.useFakeTimers()
    vi.setSystemTime(now)
    const value = conversation({
      window_expires_at: new Date(now + 2 * 60 * 60 * 1000 + 1_000).toISOString(),
    })
    render(<StatusProbe value={value} />)

    expect(screen.getByText('Ventana abierta · quedan 2 h')).toBeInTheDocument()
    act(() => vi.advanceTimersByTime(1_001))
    expect(screen.getByText('Ventana por cerrar · quedan 1 h 59 min')).toBeInTheDocument()
  })
})
