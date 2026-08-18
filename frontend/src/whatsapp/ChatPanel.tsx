import { useEffect, useRef } from 'react'

import { Button } from '../shared/Button'
import { formatDateTime } from '../shared/formatters'
import { LoadingState } from '../shared/LoadingState'
import { conversationDisplayName } from './inbox-state'
import { MessageComposer } from './MessageComposer'
import { MessageLog } from './MessageLog'
import type { WhatsAppConversationDetail, WhatsAppMessage } from './types'
import type { NewMessageInput } from './useWhatsAppInbox'

export function ChatPanel({
  conversation,
  detailStatus,
  detailError,
  messages,
  messageStatus,
  messageError,
  hasOlderMessages,
  isLoadingOlder,
  isSending,
  sendError,
  hasFailedSend,
  isOnline,
  isContextOpen,
  isContextCollapsed,
  onBack,
  onOpenContext,
  onLoadOlder,
  onOpenTemplates,
  onRetryLoad,
  onSend,
  onRetryFailed,
  onDiscardFailed,
  onResend,
}: {
  conversation: WhatsAppConversationDetail | null
  detailStatus: 'idle' | 'loading' | 'ready' | 'error'
  detailError: string | null
  messages: WhatsAppMessage[]
  messageStatus: 'idle' | 'loading' | 'ready' | 'error'
  messageError: string | null
  hasOlderMessages: boolean
  isLoadingOlder: boolean
  isSending: boolean
  sendError: string | null
  hasFailedSend: boolean
  isOnline: boolean
  isContextOpen: boolean
  isContextCollapsed: boolean
  onBack: () => void
  onOpenContext: () => void
  onLoadOlder: () => Promise<void>
  onOpenTemplates: () => void
  onRetryLoad: () => void
  onSend: (input: NewMessageInput) => Promise<boolean>
  onRetryFailed: () => Promise<boolean>
  onDiscardFailed: () => void
  onResend: (message: WhatsAppMessage) => Promise<boolean>
}) {
  const mobileBackRef = useRef<HTMLButtonElement>(null)
  const conversationId = conversation?.id

  useEffect(() => {
    if (conversationId && window.matchMedia?.('(max-width: 767px)').matches) {
      mobileBackRef.current?.focus({ preventScroll: true })
    }
  }, [conversationId])

  if (detailStatus === 'loading') {
    return (
      <section
        className='flex min-h-0 flex-1 flex-col bg-[var(--surface-primary)]'
        aria-label='Chat activo'
      >
        <LoadingState label='Abriendo conversación…' />
      </section>
    )
  }
  if (detailStatus === 'error' || !conversation) {
    return (
      <section
        className='grid min-h-0 flex-1 place-items-center bg-[var(--surface-primary)] px-5 text-center'
        aria-label='Chat activo'
      >
        <div>
          <p className='text-sm font-semibold text-[var(--text-primary)]'>
            {detailError ? 'No pudimos abrir la conversación' : 'Seleccioná una conversación'}
          </p>
          <p className='mt-1 max-w-sm text-xs leading-5 text-[var(--text-tertiary)]'>
            {detailError ??
              'Elegí un contacto de la lista para ver sus mensajes y contexto comercial.'}
          </p>
          {detailError ? (
            <Button className='mt-4' onClick={onRetryLoad} size='compact'>
              Reintentar
            </Button>
          ) : null}
        </div>
      </section>
    )
  }

  const name = conversationDisplayName(conversation)
  return (
    <section
      aria-labelledby='active-chat-title'
      className='whatsapp-chat flex min-h-0 flex-1 flex-col bg-[var(--surface-primary)]'
    >
      <header className='flex min-h-[4.25rem] shrink-0 items-center justify-between gap-3 border-b border-[var(--subtle-border)] px-3 py-2 sm:px-4'>
        <div className='flex min-w-0 items-center gap-2'>
          <button
            aria-label='Volver a conversaciones'
            className='ui-pressable grid size-11 shrink-0 place-items-center rounded-[var(--radius-control)] text-[var(--text-secondary)] outline-none hover:bg-[var(--surface-secondary)] focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)] md:hidden'
            onClick={onBack}
            ref={mobileBackRef}
            type='button'
          >
            <svg aria-hidden='true' className='size-5' fill='none' viewBox='0 0 24 24'>
              <path
                d='m15 5-7 7 7 7'
                stroke='currentColor'
                strokeLinecap='round'
                strokeLinejoin='round'
                strokeWidth='1.7'
              />
            </svg>
          </button>
          <div className='min-w-0'>
            <h2
              className='truncate text-sm font-semibold text-[var(--text-primary)]'
              id='active-chat-title'
            >
              {name}
            </h2>
            <p className='mt-0.5 truncate text-xs text-[var(--text-tertiary)]'>
              {conversation.external_phone}
              {conversation.waiting_for_response ? ' · Espera respuesta' : ''}
            </p>
          </div>
        </div>
        <Button
          aria-controls='whatsapp-context-drawer'
          aria-expanded={isContextOpen}
          onClick={onOpenContext}
          size='compact'
          variant='ghost'
          className={isContextCollapsed ? '' : '2xl:hidden'}
        >
          Ver contexto CRM
        </Button>
      </header>

      {!isOnline ? (
        <div
          className='shrink-0 border-b border-[var(--warning-border)] bg-[var(--warning-subtle)] px-4 py-2 text-xs font-medium text-[var(--warning-text)]'
          role='status'
        >
          Sin conexión. Conservamos lo cargado y sincronizaremos al reconectar.
        </div>
      ) : null}
      {conversation.waiting_for_response ? (
        <div className='shrink-0 border-b border-[var(--warning-border)] bg-[var(--warning-subtle)] px-4 py-2 text-xs text-[var(--warning-text)]'>
          <strong>Respuesta pendiente.</strong>{' '}
          {conversation.waiting_since_at
            ? `Desde ${formatDateTime(conversation.waiting_since_at)}.`
            : 'El último mensaje funcional es del cliente.'}
        </div>
      ) : null}
      {conversation.template_required ? (
        <div
          className='shrink-0 border-b border-[var(--subtle-border)] bg-[var(--surface-secondary)] px-4 py-2 text-xs text-[var(--text-secondary)]'
          role='status'
        >
          La ventana de respuesta libre está cerrada. Se requiere un template aprobado
          {conversation.window_expires_at
            ? ` desde ${formatDateTime(conversation.window_expires_at)}`
            : ''}
          .
        </div>
      ) : null}

      <MessageLog
        key={`messages-${conversation.id}`}
        error={messageError}
        hasOlder={hasOlderMessages}
        isLoadingOlder={isLoadingOlder}
        isSending={isSending}
        messages={messages}
        onLoadOlder={onLoadOlder}
        onResend={(message) => void onResend(message)}
        onRetry={onRetryLoad}
        status={messageStatus}
      />
      <MessageComposer
        key={`composer-${conversation.id}`}
        conversation={conversation}
        hasFailedSend={hasFailedSend}
        isOnline={isOnline}
        isSending={isSending}
        onDiscardFailed={onDiscardFailed}
        onOpenTemplates={onOpenTemplates}
        onRetryFailed={onRetryFailed}
        onSend={onSend}
        sendError={sendError}
      />
    </section>
  )
}
