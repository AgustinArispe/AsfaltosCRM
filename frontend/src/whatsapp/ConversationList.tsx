import { Button } from '../shared/Button'
import { Icon } from '../shared/Icon'
import { InlineFeedback, LoadingState } from '../shared/StatusStates'
import { conversationActivityLabel, conversationDisplayName } from './inbox-state'
import { formatInboxActivity } from './presentation'
import type { WhatsAppConversationSummary } from './types'

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
        'whatsapp-conversation-row ui-pressable w-full px-3 py-3 text-left outline-none focus-visible:z-10 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--focus-ring)]',
        isSelected
          ? 'whatsapp-conversation-row--selected'
          : 'bg-transparent hover:bg-[var(--surface-hover)]',
        conversation.waiting_for_response ? 'whatsapp-conversation-row--waiting' : '',
      ].join(' ')}
      onClick={onSelect}
      id={`whatsapp-conversation-${conversation.id}`}
      type='button'
    >
      <span className='flex items-start justify-between gap-3'>
        <span className='min-w-0'>
          <span className='block truncate text-sm font-semibold text-[var(--text-primary)]'>
            {name}
          </span>
          {conversation.customer?.company ? (
            <span className='mt-0.5 block truncate text-xs text-[var(--text-tertiary)]'>
              {conversation.customer.company}
            </span>
          ) : null}
        </span>
        <time
          className='shrink-0 text-[0.6875rem] font-medium text-[var(--text-tertiary)]'
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
              ? 'whatsapp-conversation-row__waiting font-semibold text-[var(--warning-text)]'
              : conversation.resolution_status === 'NEEDS_REVIEW'
                ? 'font-semibold text-[var(--destructive-text)]'
                : 'text-[var(--text-tertiary)]',
          ].join(' ')}
        >
          {conversation.waiting_for_response ? (
            <Icon className='mr-1 inline size-3.5' name='clock' />
          ) : null}
          {conversationActivityLabel(conversation)}
        </span>
        {conversation.unread_count > 0 ? (
          <span
            aria-label={`${conversation.unread_count} mensajes sin leer`}
            className='grid min-h-5 min-w-5 shrink-0 place-items-center rounded-full bg-[var(--accent)] px-1.5 text-[0.6875rem] font-bold text-[var(--on-accent)]'
            role='status'
          >
            {conversation.unread_count > 99 ? '99+' : conversation.unread_count}
          </span>
        ) : (
          <span className='shrink-0 text-[0.6875rem] text-[var(--text-tertiary)]'>
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
      className='whatsapp-inbox flex min-h-0 flex-col border-e border-[var(--divider)] bg-[var(--surface-secondary)]'
    >
      <div className='shrink-0 border-b border-[var(--subtle-border)] px-3 py-3'>
        <div className='flex items-center justify-between gap-3'>
          <h2
            className='text-sm font-semibold text-[var(--text-primary)]'
            id='whatsapp-conversations-title'
          >
            Conversaciones
          </h2>
          <span className='text-xs tabular-nums text-[var(--text-tertiary)]'>
            {conversations.length}
          </span>
        </div>
        <label className='relative mt-3 block'>
          <span className='sr-only'>Buscar conversaciones</span>
          <span className='pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)]'>
            <Icon className='size-4' name='search' />
          </span>
          <input
            className='ui-field pl-9 text-sm'
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder='Buscar cliente o teléfono'
            type='search'
            value={search}
          />
        </label>
        <fieldset className='mt-2 flex gap-2'>
          <legend className='sr-only'>Filtros de conversaciones</legend>
          <button
            aria-pressed={waitingOnly}
            className={[
              'ui-pressable min-h-9 flex-1 rounded-[var(--radius-control)] border px-2 text-xs font-semibold outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]',
              waitingOnly
                ? 'border-[var(--warning-border)] bg-[var(--warning-subtle)] text-[var(--warning-text)]'
                : 'border-[var(--subtle-border)] bg-[var(--surface-primary)] text-[var(--text-secondary)] hover:bg-[var(--surface-interactive)]',
            ].join(' ')}
            onClick={() => onWaitingChange(!waitingOnly)}
            type='button'
          >
            Esperando
          </button>
          <button
            aria-pressed={unreadOnly}
            className={[
              'ui-pressable min-h-9 flex-1 rounded-[var(--radius-control)] border px-2 text-xs font-semibold outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]',
              unreadOnly
                ? 'border-[var(--strong-border)] bg-[var(--surface-selected)] text-[var(--text-primary)]'
                : 'border-[var(--subtle-border)] bg-[var(--surface-primary)] text-[var(--text-secondary)] hover:bg-[var(--surface-interactive)]',
            ].join(' ')}
            onClick={() => onUnreadChange(!unreadOnly)}
            type='button'
          >
            No leídas
          </button>
        </fieldset>
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
            <p className='text-sm font-semibold text-[var(--text-primary)]'>
              No pudimos cargar la bandeja
            </p>
            <p className='mt-1 text-xs leading-5 text-[var(--text-tertiary)]'>
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
              className='mx-auto size-7 text-[var(--text-tertiary)]'
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
            <p className='mt-3 text-sm font-semibold text-[var(--text-primary)]'>
              No hay conversaciones para mostrar
            </p>
            <p className='mt-1 text-xs leading-5 text-[var(--text-tertiary)]'>
              Probá quitando filtros o cambiando la búsqueda.
            </p>
          </div>
        ) : (
          <ul aria-label='Conversaciones de WhatsApp' className='divide-y divide-[var(--divider)]'>
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
          <div className='border-t border-[var(--divider)] p-3 text-center'>
            <Button onClick={onLoadMore} size='compact'>
              Cargar más conversaciones
            </Button>
          </div>
        ) : null}
      </div>
    </section>
  )
}
