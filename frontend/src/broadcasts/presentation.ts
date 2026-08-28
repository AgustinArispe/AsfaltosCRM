import type { Broadcast, BroadcastAttempt, BroadcastAuditEvent, RecipientStatus } from './types'

export type BroadcastStatusPresentation = {
  label: string
  tone: 'neutral' | 'quoted' | 'negotiation' | 'won' | 'lost'
}

export function broadcastStatusPresentation(
  broadcast: Broadcast,
  isValidUnconfirmed = false,
): BroadcastStatusPresentation {
  if (broadcast.status === 'DRAFT') {
    return isValidUnconfirmed
      ? { label: 'Listo para confirmar', tone: 'quoted' }
      : { label: 'Borrador', tone: 'neutral' }
  }
  if (broadcast.status === 'CONFIRMED') {
    return { label: 'Listo para enviar', tone: 'quoted' }
  }
  if (broadcast.status === 'PROCESSING') {
    return { label: 'Enviando', tone: 'negotiation' }
  }
  const hasIncidents = Boolean(
    broadcast.outcomes && (broadcast.outcomes.failed > 0 || broadcast.outcomes.unknown > 0),
  )
  return hasIncidents
    ? { label: 'Completado con incidencias', tone: 'lost' }
    : { label: 'Completado', tone: 'won' }
}

const RECIPIENT_PRESENTATION: Record<RecipientStatus, BroadcastStatusPresentation> = {
  DRAFT: { label: 'Pendiente', tone: 'neutral' },
  READY: { label: 'Listo', tone: 'quoted' },
  IN_PROGRESS: { label: 'Enviando', tone: 'negotiation' },
  ACCEPTED: { label: 'Aceptado', tone: 'negotiation' },
  SENT: { label: 'Enviado', tone: 'negotiation' },
  DELIVERED: { label: 'Entregado', tone: 'won' },
  READ: { label: 'Leído', tone: 'won' },
  FAILED: { label: 'Fallido', tone: 'lost' },
  UNKNOWN: { label: 'Entrega incierta', tone: 'neutral' },
  BLOCKED: { label: 'Excluido', tone: 'neutral' },
}

export function recipientStatusPresentation(status: RecipientStatus): BroadcastStatusPresentation {
  return RECIPIENT_PRESENTATION[status]
}

function sentenceCaseCode(value: string): string {
  const normalized = value.trim().toLocaleLowerCase('es-AR').replaceAll('_', ' ')
  return normalized
    ? normalized[0]?.toLocaleUpperCase('es-AR') + normalized.slice(1)
    : 'Sin detalle'
}

export function attemptOutcomeLabel(attempt: BroadcastAttempt): string {
  const known: Record<string, string> = {
    ACCEPTED: 'Aceptado',
    SENT: 'Enviado',
    DELIVERED: 'Entregado',
    READ: 'Leído',
    FAILED: 'Fallido',
    UNKNOWN: 'Entrega incierta',
    BLOCKED: 'Excluido',
  }
  return known[attempt.outcome] ?? sentenceCaseCode(attempt.outcome)
}

export function auditEventLabel(event: BroadcastAuditEvent): string {
  const known: Record<string, string> = {
    CREATED: 'Envío creado',
    UPDATED: 'Borrador actualizado',
    RECIPIENTS_SELECTED: 'Clientes seleccionados',
    VALIDATED: 'Elegibilidad revisada',
    CONFIRMED: 'Envío confirmado',
    STARTED: 'Envío iniciado',
    PROCESSED: 'Lote procesado',
    RETRIED: 'Reintento solicitado',
    COMPLETED: 'Envío completado',
  }
  return known[event.event_type] ?? sentenceCaseCode(event.event_type)
}

export function safeReasonLabel(reason: string): string {
  return sentenceCaseCode(reason)
}

export function templateCategoryLabel(category: string): string {
  const known: Record<string, string> = {
    MARKETING: 'Marketing',
    UTILITY: 'Utilidad',
    AUTHENTICATION: 'Autenticación',
  }
  return known[category] ?? sentenceCaseCode(category)
}

export function templateLanguageLabel(language: string): string {
  const known: Record<string, string> = {
    es: 'Español',
    es_AR: 'Español (Argentina)',
    en: 'Inglés',
    en_US: 'Inglés (Estados Unidos)',
    pt_BR: 'Portugués (Brasil)',
  }
  return known[language] ?? language.replace('_', '-')
}
