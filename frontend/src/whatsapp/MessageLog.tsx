import { useCallback, useEffect, useRef, useState } from 'react'

import { Button } from '../shared/Button'
import { LoadingState } from '../shared/LoadingState'
import { MessageBubble } from './MessageBubble'
import type { WhatsAppMessage } from './types'

const BOTTOM_THRESHOLD_PX = 72

export function MessageLog({
  messages,
  status,
  error,
  hasOlder,
  isLoadingOlder,
  isSending,
  onLoadOlder,
  onRetry,
  onResend,
}: {
  messages: WhatsAppMessage[]
  status: 'idle' | 'loading' | 'ready' | 'error'
  error: string | null
  hasOlder: boolean
  isLoadingOlder: boolean
  isSending: boolean
  onLoadOlder: () => Promise<void>
  onRetry: () => void
  onResend: (message: WhatsAppMessage) => void
}) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const previousLastMessageIdRef = useRef<number | null>(null)
  const initialScrollDoneRef = useRef(false)
  const [isNearBottom, setIsNearBottom] = useState(true)
  const [hasUnseenMessages, setHasUnseenMessages] = useState(false)
  const [announceUpdates, setAnnounceUpdates] = useState(false)

  const scrollToBottom = useCallback(() => {
    const node = scrollRef.current
    if (!node) return
    node.scrollTop = node.scrollHeight
    setHasUnseenMessages(false)
    setIsNearBottom(true)
  }, [])

  useEffect(() => {
    if (status !== 'ready' || initialScrollDoneRef.current) return
    initialScrollDoneRef.current = true
    scrollToBottom()
    const frame = window.requestAnimationFrame(() => setAnnounceUpdates(true))
    return () => window.cancelAnimationFrame(frame)
  }, [scrollToBottom, status])

  useEffect(() => {
    const lastId = messages.at(-1)?.id ?? null
    const previousId = previousLastMessageIdRef.current
    previousLastMessageIdRef.current = lastId
    if (!initialScrollDoneRef.current || previousId === null || lastId === previousId) {
      return
    }
    if (isNearBottom) {
      window.requestAnimationFrame(scrollToBottom)
    } else {
      setHasUnseenMessages(true)
    }
  }, [isNearBottom, messages, scrollToBottom])

  const handleScroll = () => {
    const node = scrollRef.current
    if (!node) return
    const nearBottom = node.scrollHeight - node.scrollTop - node.clientHeight <= BOTTOM_THRESHOLD_PX
    setIsNearBottom(nearBottom)
    if (nearBottom) setHasUnseenMessages(false)
  }

  const handleLoadOlder = async () => {
    const node = scrollRef.current
    const priorHeight = node?.scrollHeight ?? 0
    await onLoadOlder()
    window.requestAnimationFrame(() => {
      if (node) node.scrollTop += node.scrollHeight - priorHeight
    })
  }

  if (status === 'loading') {
    return <LoadingState label='Cargando mensajes…' />
  }
  if (status === 'error' && messages.length === 0) {
    return (
      <div className='grid min-h-0 flex-1 place-items-center px-5 text-center'>
        <div>
          <p className='text-sm font-semibold text-[var(--text-primary)]'>
            No pudimos cargar los mensajes
          </p>
          <p className='mt-1 text-xs text-[var(--text-tertiary)]'>{error}</p>
          <Button className='mt-4' onClick={onRetry} size='compact'>
            Reintentar
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className='relative min-h-0 flex-1 bg-[var(--surface-interactive)]'>
      <div
        aria-label='Historial de mensajes'
        aria-live={announceUpdates ? 'polite' : 'off'}
        aria-relevant='additions'
        className='h-full overflow-y-auto px-3 py-4 sm:px-5'
        onScroll={handleScroll}
        ref={scrollRef}
        role='log'
      >
        {hasOlder ? (
          <div className='mb-4 text-center'>
            <Button
              disabled={isLoadingOlder}
              onClick={() => void handleLoadOlder()}
              size='compact'
              variant='ghost'
            >
              {isLoadingOlder ? 'Cargando…' : 'Cargar mensajes anteriores'}
            </Button>
          </div>
        ) : null}
        {error ? (
          <p
            className='mb-3 text-center text-xs font-medium text-[var(--destructive-text)]'
            role='status'
          >
            {error}
          </p>
        ) : null}
        {messages.length === 0 ? (
          <div className='grid min-h-full place-items-center text-center'>
            <div>
              <p className='text-sm font-semibold text-[var(--text-primary)]'>
                Todavía no hay mensajes disponibles
              </p>
              <p className='mt-1 text-xs text-[var(--text-tertiary)]'>
                La conversación aparecerá aquí cuando tenga actividad.
              </p>
            </div>
          </div>
        ) : (
          <ol className='space-y-2.5'>
            {messages.map((message) => (
              <li key={message.id}>
                <MessageBubble isSending={isSending} message={message} onResend={onResend} />
              </li>
            ))}
          </ol>
        )}
      </div>
      {hasUnseenMessages ? (
        <Button
          className='absolute bottom-3 left-1/2 -translate-x-1/2 shadow-sm'
          onClick={scrollToBottom}
          size='compact'
          variant='primary'
        >
          Hay mensajes nuevos
        </Button>
      ) : null}
    </div>
  )
}
