import { describe, expect, it } from 'vitest'
import {
  auditEventLabel,
  broadcastStatusPresentation,
  recipientStatusPresentation,
} from './presentation'
import type { Broadcast } from './types'

const base: Broadcast = {
  id: 1,
  label: 'Seguimiento',
  status: 'DRAFT',
  version: 1,
  template_external_id: 'template-1',
  template_name: 'seguimiento',
  template_language: 'es_AR',
  template_category: 'UTILITY',
  template_header_type: null,
  template_header_media_required: false,
  header_media_ref: null,
  parameters: [],
  recipient_count: 2,
  outcomes: null,
  validated_at: null,
  confirmed_at: null,
  started_at: null,
  created_at: '2026-08-28T12:00:00Z',
  updated_at: '2026-08-28T12:00:00Z',
}

describe('broadcast presentation', () => {
  it('derives workflow language without exposing backend statuses', () => {
    expect(broadcastStatusPresentation(base).label).toBe('Borrador')
    expect(broadcastStatusPresentation(base, true).label).toBe('Listo para confirmar')
    expect(broadcastStatusPresentation({ ...base, status: 'CONFIRMED' }).label).toBe(
      'Listo para enviar',
    )
    expect(broadcastStatusPresentation({ ...base, status: 'PROCESSING' }).label).toBe('Enviando')
  })

  it('makes completed incidents and recipient uncertainty explicit', () => {
    expect(
      broadcastStatusPresentation({
        ...base,
        status: 'COMPLETED',
        outcomes: {
          selected: 2,
          accepted: 1,
          sent: 1,
          delivered: 0,
          read: 0,
          failed: 0,
          unknown: 1,
          skipped: 0,
        },
      }).label,
    ).toBe('Completado con incidencias')
    expect(recipientStatusPresentation('UNKNOWN').label).toBe('Entrega incierta')
  })

  it('translates audit evidence', () => {
    expect(
      auditEventLabel({
        id: 1,
        event_type: 'PROCESSED',
        reason_code: null,
        actor_user_id: 2,
        affected_count: 1,
        occurred_at: '2026-08-28T12:00:00Z',
      }),
    ).toBe('Lote procesado')
  })
})
