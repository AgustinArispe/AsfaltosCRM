import { Button } from '../shared/Button'
import { InlineFeedback } from '../shared/InlineFeedback'
import { LoadingState } from '../shared/LoadingState'
import { conversationActivityLabel, conversationDisplayName } from './inbox-state'
import { formatInboxActivity } from './presentation'
import type { WhatsAppConversationSummary } from './types'

function SearchIcon() {
  return (
    <svg aria-hidden='true' className='size-4' fill='none' viewBox='0 0 20 20'>
      <circle cx='8.5' cy='8.5' r='5.5' stroke='currentColor' strokeWidth='1.6' />
      <path d='m12.5 12.5 4 4' stroke='currentColor' strokeLinecap='round' strokeWidth='1.6' />
    </svg>
  )
}

function ConversationRow({
  conversation,
  isSelected,
  onSelect,
}: {
  conversation: WhatsAppConversationSummary
  isSelected: boolean
  onSelect: () => void
}) {
  const name = conversationDisplayName(conversation)
  return (
    <button
      aria-current={isSelected ? 'true' : undefined}
      className={[
        'ui-pressable w-full border-l-2 px-3 py-3 text-left outline-none focus-visible:z-10 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-slate-500',
        isSelected
          ? 'border-l-slate-700 bg-slate-100'
          : 'border-l-transparent bg-white hover:bg-slate-50',
      ].join(' ')}
      onClick={onSelect}
      id={`whatsapp-conversation-${conversation.id}`}
      type='button'
    >
      <span className='flex items-start justify-between gap-3'>
        <span className='min-w-0'>
          <span className='block truncate text-sm font-semibold text-slate-950'>{name}</span>
          {conversation.customer?.company ? (
            <span className='mt-0.5 block truncate text-xs text-slate-500'>
              {conversation.customer.company}
            </span>
          ) : null}
        </span>
        <time
          className='shrink-0 text-[0.6875rem] font-medium text-slate-500'
          dateTime={conversation.last_message_at ?? undefined}
          title={conversation.last_message_at ?? undefined}
        >
          {formatInboxActivity(conversation.last_message_at)}
        </time>
      </span>

      <span className='mt-2 flex items-center justify-between gap-3'>
        <span
          className={[
            'min-w-0 truncate text-xs',
            conversation.waiting_for_response
              ? 'font-semibold text-amber-800'
              : conversation.resolution_status === 'NEEDS_REVIEW'
                ? 'font-semibold text-rose-700'
                : 'text-slate-500',
          ].join(' ')}
        >
          {conversationActivityLabel(conversation)}
        </span>
        {conversation.unread_count > 0 ? (
          <span
            aria-label={`${conversation.unread_count} mensajes sin leer`}
            className='grid min-h-5 min-w-5 shrink-0 place-items-center rounded-full bg-slate-800 px-1.5 text-[0.6875rem] font-bold text-white'
          >
            {conversation.unread_count > 99 ? '99+' : conversation.unread_count}
          </span>
        ) : (
          <span className='shrink-0 text-[0.6875rem] text-slate-400'>
            {conversation.external_phone}
          </span>
        )}
      </span>
    </button>
  )
}

export function ConversationList({
  conversations,
  status,
  error,
  selectedConversationId,
  search,
  waitingOnly,
  unreadOnly,
  hasMore,
  onSearchChange,
  onWaitingChange,
  onUnreadChange,
  onSelect,
  onLoadMore,
  onRetry,
}: {
  conversations: WhatsAppConversationSummary[]
  status: 'idle' | 'loading' | 'ready' | 'error'
  error: string | null
  selectedConversationId: number | null
  search: string
  waitingOnly: boolean
  unreadOnly: boolean
  hasMore: boolean
  onSearchChange: (value: string) => void
  onWaitingChange: (value: boolean) => void
  onUnreadChange: (value: boolean) => void
  onSelect: (conversationId: number) => void
  onLoadMore: () => void
  onRetry: () => void
}) {
  const isInitialLoading = status === 'loading' && conversations.length === 0
  return (
    <section
      aria-labelledby='whatsapp-conversations-title'
      className='flex min-h-0 flex-col border-r border-slate-200 bg-white'
    >
      <div className='shrink-0 border-b border-slate-200 px-3 py-3'>
        <div className='flex items-center justify-between gap-3'>
          <h2 className='text-sm font-semibold text-slate-950' id='whatsapp-conversations-title'>
            Conversaciones
          </h2>
          <span className='text-xs tabular-nums text-slate-500'>{conversations.length}</span>
        </div>
        <label className='relative mt-3 block'>
          <span className='sr-only'>Buscar conversaciones</span>
          <span className='pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500'>
            <SearchIcon />
          </span>
          <input
            className='ui-field pl-9 text-sm'
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder='Buscar cliente o teléfono'
            type='search'
            value={search}
          />
        </label>
        <div aria-label='Filtros de conversaciones' className='mt-2 flex gap-2' role='group'>
          <button
            aria-pressed={waitingOnly}
            className={[
              'ui-pressable min-h-11 flex-1 rounded-[4px] border px-2 text-xs font-semibold outline-none focus-visible:ring-2 focus-visible:ring-slate-500',
              waitingOnly
                ? 'border-amber-300 bg-amber-50 text-amber-900'
                : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50',
            ].join(' ')}
            onClick={() => onWaitingChange(!waitingOnly)}
            type='button'
          >
            Esperando
          </button>
          <button
            aria-pressed={unreadOnly}
            className={[
              'ui-pressable min-h-11 flex-1 rounded-[4px] border px-2 text-xs font-semibold outline-none focus-visible:ring-2 focus-visible:ring-slate-500',
              unreadOnly
                ? 'border-slate-600 bg-slate-700 text-white'
                : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50',
            ].join(' ')}
            onClick={() => onUnreadChange(!unreadOnly)}
            type='button'
          >
            No leídas
          </button>
        </div>
      </div>

      {error && conversations.length > 0 ? (
        <div className='shrink-0 px-3 pt-3'>
          <InlineFeedback message={error} />
        </div>
      ) : null}

      <div aria-busy={status === 'loading'} className='min-h-0 flex-1 overflow-y-auto'>
        {isInitialLoading ? (
          <LoadingState label='Cargando conversaciones…' />
        ) : status === 'error' && conversations.length === 0 ? (
          <div className='px-4 py-7 text-center'>
            <p className='text-sm font-semibold text-slate-900'>No pudimos cargar la bandeja</p>
            <p className='mt-1 text-xs leading-5 text-slate-500'>
              {error ?? 'Revisá la conexión e intentá nuevamente.'}
            </p>
            <Button className='mt-4' onClick={onRetry} size='compact'>
              Reintentar
            </Button>
          </div>
        ) : conversations.length === 0 ? (
          <div className='px-5 py-8 text-center'>
            <svg
              aria-hidden='true'
              className='mx-auto size-7 text-slate-400'
              fill='none'
              viewBox='0 0 24 24'
            >
              <path
                d='M5 6.5h14v9H9l-4 3v-12Z'
                stroke='currentColor'
                strokeLinejoin='round'
                strokeWidth='1.5'
              />
            </svg>
            <p className='mt-3 text-sm font-semibold text-slate-800'>
              No hay conversaciones para mostrar
            </p>
            <p className='mt-1 text-xs leading-5 text-slate-500'>
              Probá quitando filtros o cambiando la búsqueda.
            </p>
          </div>
        ) : (
          <ul aria-label='Conversaciones de WhatsApp' className='divide-y divide-slate-100'>
            {conversations.map((conversation) => (
              <li key={conversation.id}>
                <ConversationRow
                  conversation={conversation}
                  isSelected={conversation.id === selectedConversationId}
                  onSelect={() => onSelect(conversation.id)}
                />
              </li>
            ))}
          </ul>
        )}
        {hasMore ? (
          <div className='border-t border-slate-100 p-3 text-center'>
            <Button onClick={onLoadMore} size='compact'>
              Cargar más conversaciones
            </Button>
          </div>
        ) : null}
      </div>
    </section>
  )
}
