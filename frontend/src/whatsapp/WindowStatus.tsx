import { useEffect, useState } from 'react'

import type { WhatsAppConversationSummary } from './types'

export const WINDOW_CLOSING_SOON_MS = 2 * 60 * 60 * 1000

export type ConversationWindowStatus = {
  kind: 'OPEN' | 'CLOSING_SOON' | 'CLOSED'
  label: string
  notice: string | null
}

function remainingLabel(remainingMs: number): string {
  const remainingMinutes = Math.max(0, Math.floor(remainingMs / 60_000))
  if (remainingMinutes < 1) return 'queda menos de 1 min'
  const hours = Math.floor(remainingMinutes / 60)
  const minutes = remainingMinutes % 60
  if (hours === 0) return `quedan ${minutes} min`
  if (minutes === 0) return `quedan ${hours} h`
  return `quedan ${hours} h ${minutes} min`
}

export function conversationWindowStatus(
  conversation: WhatsAppConversationSummary,
  now = Date.now(),
): ConversationWindowStatus {
  const expiresAt = conversation.window_expires_at
    ? new Date(conversation.window_expires_at).getTime()
    : null
  const remainingMs = expiresAt === null || Number.isNaN(expiresAt) ? null : expiresAt - now

  if (!conversation.can_send_freeform) {
    return {
      kind: 'CLOSED',
      label: 'Ventana cerrada',
      notice:
        'La ventana de 24 horas está cerrada. Esperá una respuesta o usá una plantilla aprobada.',
    }
  }
  if (remainingMs !== null && remainingMs <= 0) {
    return { kind: 'OPEN', label: 'Ventana abierta', notice: null }
  }
  if (remainingMs !== null && remainingMs <= WINDOW_CLOSING_SOON_MS) {
    return {
      kind: 'CLOSING_SOON',
      label: `Ventana por cerrar · ${remainingLabel(remainingMs)}`,
      notice: 'La ventana de respuesta cierra en menos de 2 horas.',
    }
  }
  return {
    kind: 'OPEN',
    label:
      remainingMs === null ? 'Ventana abierta' : `Ventana abierta · ${remainingLabel(remainingMs)}`,
    notice: null,
  }
}

function nextUpdateDelay(conversation: WhatsAppConversationSummary, now: number): number | null {
  if (!conversation.window_expires_at || !conversation.can_send_freeform) return null
  const expiresAt = new Date(conversation.window_expires_at).getTime()
  if (Number.isNaN(expiresAt)) return null
  const remainingMs = expiresAt - now
  if (remainingMs <= 0) return null
  const untilMinuteBoundary = 60_000 - (now % 60_000)
  const untilWarning = remainingMs - WINDOW_CLOSING_SOON_MS
  return Math.max(
    1,
    Math.min(untilMinuteBoundary, remainingMs, untilWarning > 0 ? untilWarning : Infinity),
  )
}

export function useConversationWindowStatus(
  conversation: WhatsAppConversationSummary | null,
): ConversationWindowStatus | null {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    if (!conversation) return
    const delay = nextUpdateDelay(conversation, now)
    if (delay === null) return
    const timer = window.setTimeout(() => setNow(Date.now()), delay + 1)
    return () => window.clearTimeout(timer)
  }, [conversation, now])

  return conversation ? conversationWindowStatus(conversation, now) : null
}

export function WindowStatus({ status }: { status: ConversationWindowStatus }) {
  const tone =
    status.kind === 'CLOSED'
      ? 'border-[var(--destructive-text)]/30 bg-[var(--danger-surface)] text-[var(--destructive-text)]'
      : status.kind === 'CLOSING_SOON'
        ? 'border-[var(--warning-text)]/30 bg-[var(--warning-surface)] text-[var(--warning-text)]'
        : 'border-[var(--success-text)]/25 bg-[var(--success-surface)] text-[var(--success-text)]'

  return (
    <div className='min-w-0 text-right'>
      <span
        className={`inline-flex max-w-full items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${tone}`}
      >
        {status.label}
      </span>
      {status.notice ? (
        <p className='mt-1 text-xs leading-4 text-[var(--text-secondary)]'>{status.notice}</p>
      ) : null}
    </div>
  )
}
