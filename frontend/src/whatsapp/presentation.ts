import type { WhatsAppConversationSummary, WhatsAppMessage } from './types'

const SHORT_TIME_FORMATTER = new Intl.DateTimeFormat('es-AR', {
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
  timeZone: 'America/Argentina/Buenos_Aires',
})

const SHORT_DATE_FORMATTER = new Intl.DateTimeFormat('es-AR', {
  day: '2-digit',
  month: '2-digit',
  timeZone: 'America/Argentina/Buenos_Aires',
})

export function formatInboxActivity(value: string | null, now = new Date()): string {
  if (!value) return '—'
  const date = new Date(value)
  const sameDay =
    date.toLocaleDateString('en-CA', {
      timeZone: 'America/Argentina/Buenos_Aires',
    }) ===
    now.toLocaleDateString('en-CA', {
      timeZone: 'America/Argentina/Buenos_Aires',
    })
  return sameDay ? SHORT_TIME_FORMATTER.format(date) : SHORT_DATE_FORMATTER.format(date)
}

export function formatFileSize(bytes: number | null): string | null {
  if (bytes === null) return null
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toLocaleString('es-AR', {
    maximumFractionDigits: 1,
  })} MB`
}

export type MessageStatusPresentation = {
  label: string
  tone: 'neutral' | 'success' | 'danger' | 'warning'
}

export function messageStatusPresentation(
  message: WhatsAppMessage,
): MessageStatusPresentation | null {
  if (message.direction === 'INBOUND') return null
  const { dispatch_state: dispatch, provider_state: provider } = message.status
  if (provider === 'READ') return { label: 'Leído', tone: 'success' }
  if (provider === 'DELIVERED') return { label: 'Entregado', tone: 'success' }
  if (provider === 'SENT') return { label: 'Enviado', tone: 'neutral' }
  if (provider === 'FAILED' || dispatch === 'DEFINITIVE_FAILED') {
    return { label: 'Falló', tone: 'danger' }
  }
  if (dispatch === 'UNKNOWN') {
    return { label: 'Aceptación sin confirmar', tone: 'warning' }
  }
  if (dispatch === 'ACCEPTED') return { label: 'Aceptado', tone: 'neutral' }
  return { label: 'Enviando', tone: 'neutral' }
}

export function canExplicitlyResend(message: WhatsAppMessage): boolean {
  return (
    message.direction === 'OUTBOUND' &&
    (message.status.dispatch_state === 'UNKNOWN' ||
      message.status.dispatch_state === 'DEFINITIVE_FAILED' ||
      message.status.provider_state === 'FAILED')
  )
}

export function composerDisabledReason(
  conversation: WhatsAppConversationSummary,
  isOnline: boolean,
  isSending: boolean,
): string | null {
  if (!isOnline) return 'Sin conexión. Reconectate para enviar.'
  if (isSending) return 'El mensaje se está enviando.'
  if (conversation.resolution_status === 'NEEDS_REVIEW') {
    return 'La identidad del contacto requiere revisión antes de responder.'
  }
  if (!conversation.customer?.is_available) {
    return 'El cliente no está disponible para responder.'
  }
  if (!conversation.can_send_freeform) {
    return 'La ventana de respuesta está cerrada. Se requiere un template aprobado.'
  }
  return null
}
