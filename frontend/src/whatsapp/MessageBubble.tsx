import { Button } from '../shared/Button'
import { formatDateTime } from '../shared/formatters'
import { canExplicitlyResend, formatFileSize, messageStatusPresentation } from './presentation'
import type { WhatsAppMessage } from './types'
import { useAuthenticatedMedia } from './useAuthenticatedMedia'

const STATUS_TONE_CLASSES = {
  neutral: 'text-[var(--text-tertiary)]',
  success: 'text-[var(--success-text)]',
  danger: 'text-[var(--destructive-text)]',
  warning: 'text-[var(--warning-text)]',
} as const

function AttachmentContent({ message }: { message: WhatsAppMessage }) {
  const attachment = message.attachment
  const { objectUrl, isLoading, error } = useAuthenticatedMedia(
    attachment?.is_available ? attachment.content_url : null,
  )
  if (!attachment) return null
  const size = formatFileSize(attachment.size_bytes)

  if (!attachment.is_available) {
    return (
      <p className='mt-2 rounded-[var(--radius-control)] border border-[var(--subtle-border)] bg-[var(--surface-primary)] px-3 py-2 text-xs text-[var(--text-secondary)]'>
        Archivo todavía no disponible
      </p>
    )
  }
  if (isLoading) {
    return (
      <p className='mt-2 text-xs text-[var(--text-tertiary)]' role='status'>
        Cargando archivo…
      </p>
    )
  }
  if (error || !objectUrl) {
    return (
      <p className='mt-2 text-xs font-medium text-[var(--destructive-text)]' role='alert'>
        No pudimos abrir el archivo.
      </p>
    )
  }
  if (message.message_type === 'IMAGE') {
    return (
      <a
        className='mt-2 block rounded-[var(--radius-control)] outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)] focus-visible:ring-offset-2'
        href={objectUrl}
        rel='noreferrer'
        target='_blank'
      >
        <img
          alt={attachment.filename ? `Imagen ${attachment.filename}` : 'Imagen adjunta'}
          className='max-h-72 max-w-full rounded-[var(--radius-control)] object-contain'
          src={objectUrl}
        />
      </a>
    )
  }
  return (
    <a
      className='mt-2 flex min-h-11 items-center gap-3 rounded-[var(--radius-control)] border border-[var(--subtle-border)] bg-[var(--surface-primary)] px-3 py-2 text-left outline-none hover:border-[var(--strong-border)] focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]'
      download={attachment.filename ?? 'documento.pdf'}
      href={objectUrl}
    >
      <svg
        aria-hidden='true'
        className='size-5 shrink-0 text-[var(--text-secondary)]'
        fill='none'
        viewBox='0 0 24 24'
      >
        <path
          d='M7 3.5h7l4 4v13H7v-17Z'
          stroke='currentColor'
          strokeLinejoin='round'
          strokeWidth='1.5'
        />
        <path
          d='M14 3.5v4h4M9.5 14h5M9.5 17h4'
          stroke='currentColor'
          strokeLinecap='round'
          strokeWidth='1.5'
        />
      </svg>
      <span className='min-w-0'>
        <span className='block truncate text-xs font-semibold text-[var(--text-primary)]'>
          {attachment.filename ?? 'Documento PDF'}
        </span>
        <span className='block text-[0.6875rem] text-[var(--text-tertiary)]'>
          {[attachment.mime_type, size].filter(Boolean).join(' · ')}
        </span>
      </span>
    </a>
  )
}

export function MessageBubble({
  message,
  isSending,
  onResend,
}: {
  message: WhatsAppMessage
  isSending: boolean
  onResend: (message: WhatsAppMessage) => void
}) {
  const isOutbound = message.direction === 'OUTBOUND'
  const status = messageStatusPresentation(message)
  const resend = canExplicitlyResend(message)
  return (
    <article
      aria-label={`${isOutbound ? 'Mensaje enviado' : 'Mensaje recibido'} el ${formatDateTime(message.message_at)}`}
      className={[
        `whatsapp-message whatsapp-message--${isOutbound ? 'outbound' : 'inbound'} max-w-[min(38rem,88%)] rounded-[var(--radius-surface)] px-3 py-2.5`,
        isOutbound
          ? 'ml-auto bg-[var(--surface-selected)]'
          : 'mr-auto bg-[var(--surface-raised)] shadow-[var(--shadow-subtle)]',
      ].join(' ')}
    >
      {message.is_retry ? (
        <p className='mb-1 text-[0.6875rem] font-semibold text-[var(--text-tertiary)]'>
          Reenvío del mensaje #{message.retry_of_message_id}
        </p>
      ) : null}
      {message.body ? (
        <p className='whitespace-pre-wrap break-words text-sm leading-5 text-[var(--text-primary)]'>
          {message.body}
        </p>
      ) : null}
      {message.template_name ? (
        <p className='text-sm leading-5 text-[var(--text-primary)]'>
          Plantilla aprobada: {message.template_name}
          {message.template_language ? ` · ${message.template_language}` : ''}
        </p>
      ) : null}
      <AttachmentContent message={message} />
      <footer className='mt-1.5 flex flex-wrap items-center justify-end gap-x-2 gap-y-1 text-[0.6875rem]'>
        {isOutbound ? (
          <span className='mr-auto font-medium text-[var(--text-secondary)]'>
            {message.origin === 'BROADCAST' ? 'Envío masivo' : 'Atención humana'}
          </span>
        ) : null}
        {message.sent_by ? (
          <span className='text-[var(--text-tertiary)]'>{message.sent_by.full_name}</span>
        ) : null}
        <time className='text-[var(--text-tertiary)]' dateTime={message.message_at}>
          {formatDateTime(message.message_at)}
        </time>
        {status ? (
          <span
            className={`font-semibold ${STATUS_TONE_CLASSES[status.tone]}`}
            title={message.status.error_message ?? undefined}
          >
            {status.label}
          </span>
        ) : null}
      </footer>
      {message.status.dispatch_state === 'UNKNOWN' ? (
        <p className='mt-1 text-xs leading-5 text-[var(--warning-text)]'>
          No podemos confirmar la entrega. El mensaje podría haber llegado; no se reenviará
          automáticamente.
        </p>
      ) : null}
      {resend ? (
        <div className='mt-2 border-t border-[var(--subtle-border)]/70 pt-2 text-right'>
          <Button
            disabled={isSending}
            onClick={() => onResend(message)}
            size='compact'
            variant='ghost'
          >
            Reenviar explícitamente
          </Button>
        </div>
      ) : null}
    </article>
  )
}
