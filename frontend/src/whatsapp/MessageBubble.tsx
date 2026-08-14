import { Button } from '../shared/Button'
import { formatDateTime } from '../shared/formatters'
import { canExplicitlyResend, formatFileSize, messageStatusPresentation } from './presentation'
import type { WhatsAppMessage } from './types'
import { useAuthenticatedMedia } from './useAuthenticatedMedia'

const STATUS_TONE_CLASSES = {
  neutral: 'text-slate-500',
  success: 'text-emerald-700',
  danger: 'text-rose-700',
  warning: 'text-amber-800',
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
      <p className='mt-2 rounded-[4px] border border-slate-300 bg-white/70 px-3 py-2 text-xs text-slate-600'>
        Archivo todavía no disponible
      </p>
    )
  }
  if (isLoading) {
    return (
      <p className='mt-2 text-xs text-slate-500' role='status'>
        Cargando archivo…
      </p>
    )
  }
  if (error || !objectUrl) {
    return (
      <p className='mt-2 text-xs font-medium text-rose-700' role='alert'>
        No pudimos abrir el archivo.
      </p>
    )
  }
  if (message.message_type === 'IMAGE') {
    return (
      <a
        className='mt-2 block rounded-[4px] outline-none focus-visible:ring-2 focus-visible:ring-slate-500 focus-visible:ring-offset-2'
        href={objectUrl}
        rel='noreferrer'
        target='_blank'
      >
        <img
          alt={attachment.filename ? `Imagen ${attachment.filename}` : 'Imagen adjunta'}
          className='max-h-72 max-w-full rounded-[4px] object-contain'
          src={objectUrl}
        />
      </a>
    )
  }
  return (
    <a
      className='mt-2 flex min-h-11 items-center gap-3 rounded-[4px] border border-slate-300 bg-white/80 px-3 py-2 text-left outline-none hover:border-slate-400 focus-visible:ring-2 focus-visible:ring-slate-500'
      download={attachment.filename ?? 'documento.pdf'}
      href={objectUrl}
    >
      <svg
        aria-hidden='true'
        className='size-5 shrink-0 text-slate-600'
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
        <span className='block truncate text-xs font-semibold text-slate-800'>
          {attachment.filename ?? 'Documento PDF'}
        </span>
        <span className='block text-[0.6875rem] text-slate-500'>
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
        'max-w-[min(38rem,88%)] rounded-[6px] border px-3 py-2.5 shadow-[0_1px_1px_rgb(15_23_42_/_0.04)]',
        isOutbound ? 'ml-auto border-slate-300 bg-[#eef3f7]' : 'mr-auto border-slate-200 bg-white',
      ].join(' ')}
    >
      {message.is_retry ? (
        <p className='mb-1 text-[0.6875rem] font-semibold uppercase tracking-wide text-slate-500'>
          Reenvío del mensaje #{message.retry_of_message_id}
        </p>
      ) : null}
      {message.body ? (
        <p className='whitespace-pre-wrap break-words text-sm leading-5 text-slate-900'>
          {message.body}
        </p>
      ) : null}
      {message.template_name ? (
        <p className='text-sm leading-5 text-slate-900'>
          Plantilla aprobada: {message.template_name}
          {message.template_language ? ` · ${message.template_language}` : ''}
        </p>
      ) : null}
      <AttachmentContent message={message} />
      <footer className='mt-1.5 flex flex-wrap items-center justify-end gap-x-2 gap-y-1 text-[0.6875rem]'>
        {message.sent_by ? (
          <span className='mr-auto text-slate-500'>{message.sent_by.full_name}</span>
        ) : null}
        <time className='text-slate-500' dateTime={message.message_at}>
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
        <p className='mt-1 text-xs leading-5 text-amber-900'>
          No podemos confirmar la entrega. El mensaje podría haber llegado; no se reenviará
          automáticamente.
        </p>
      ) : null}
      {resend ? (
        <div className='mt-2 border-t border-slate-300/70 pt-2 text-right'>
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
