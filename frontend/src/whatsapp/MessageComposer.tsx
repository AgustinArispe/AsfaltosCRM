import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react'

import { buttonClassName, Button } from '../shared/Button'
import type { NewMessageInput } from './useWhatsAppInbox'
import type {
  StagedWhatsAppAttachment,
  WhatsAppConversationDetail,
} from './types'
import { composerDisabledReason, formatFileSize } from './presentation'

const IMAGE_MIME_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp'])

function stagedAttachment(file: File): StagedWhatsAppAttachment | null {
  if (file.size === 0) return null
  if (IMAGE_MIME_TYPES.has(file.type)) {
    return {
      file,
      messageType: 'IMAGE',
      previewUrl: URL.createObjectURL(file),
    }
  }
  if (file.type === 'application/pdf') {
    return { file, messageType: 'DOCUMENT', previewUrl: null }
  }
  return null
}

export function MessageComposer({
  conversation,
  isOnline,
  isSending,
  sendError,
  hasFailedSend,
  onSend,
  onRetryFailed,
  onDiscardFailed,
}: {
  conversation: WhatsAppConversationDetail
  isOnline: boolean
  isSending: boolean
  sendError: string | null
  hasFailedSend: boolean
  onSend: (input: NewMessageInput) => Promise<boolean>
  onRetryFailed: () => Promise<boolean>
  onDiscardFailed: () => void
}) {
  const [body, setBody] = useState('')
  const [attachment, setAttachment] =
    useState<StagedWhatsAppAttachment | null>(null)
  const [fileError, setFileError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const helpId = useId()
  const errorId = useId()
  const attachmentId = useId()
  const backendDisabledReason = composerDisabledReason(
    conversation,
    isOnline,
    isSending,
  )
  const disabledReason = hasFailedSend
    ? 'Hay un intento pendiente. Reintentá o descartalo antes de enviar otro mensaje.'
    : backendDisabledReason
  const hasContent = Boolean(body.trim()) || Boolean(attachment)
  const canSend = !disabledReason && hasContent

  useEffect(
    () => () => {
      if (attachment?.previewUrl) URL.revokeObjectURL(attachment.previewUrl)
    },
    [attachment],
  )

  const clearAttachment = () => {
    if (attachment?.previewUrl) URL.revokeObjectURL(attachment.previewUrl)
    setAttachment(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const resetComposer = () => {
    setBody('')
    clearAttachment()
    setFileError(null)
  }

  const submit = async () => {
    if (!canSend) return
    const success = await onSend({ body, attachment })
    if (success) resetComposer()
  }

  const retry = async () => {
    const success = await onRetryFailed()
    if (success) resetComposer()
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (
      event.key !== 'Enter' ||
      event.shiftKey ||
      event.nativeEvent.isComposing
    ) {
      return
    }
    event.preventDefault()
    void submit()
  }

  const handleFile = (file: File | undefined) => {
    if (!file) return
    const next = stagedAttachment(file)
    if (!next) {
      setFileError('Seleccioná una imagen JPG, PNG o WebP, o un documento PDF válido.')
      if (fileInputRef.current) fileInputRef.current.value = ''
      return
    }
    clearAttachment()
    setAttachment(next)
    setFileError(null)
  }

  const describedBy = [
    helpId,
    sendError || fileError ? errorId : null,
    attachment ? attachmentId : null,
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <form
      className="shrink-0 border-t border-slate-200 bg-white px-3 py-3 sm:px-4"
      onSubmit={(event) => {
        event.preventDefault()
        void submit()
      }}
    >
      {attachment ? (
        <div
          className="mb-2 flex items-center justify-between gap-3 rounded-[4px] border border-slate-200 bg-slate-50 px-3 py-2"
          id={attachmentId}
        >
          <div className="flex min-w-0 items-center gap-3">
            {attachment.previewUrl ? (
              <img
                alt={`Vista previa de ${attachment.file.name}`}
                className="size-11 rounded-[3px] object-cover"
                src={attachment.previewUrl}
              />
            ) : (
              <svg aria-hidden="true" className="size-6 shrink-0 text-slate-500" fill="none" viewBox="0 0 24 24">
                <path d="M7 3.5h7l4 4v13H7v-17Z" stroke="currentColor" strokeLinejoin="round" strokeWidth="1.5" />
                <path d="M14 3.5v4h4" stroke="currentColor" strokeWidth="1.5" />
              </svg>
            )}
            <span className="min-w-0">
              <span className="block truncate text-xs font-semibold text-slate-800">
                {attachment.file.name}
              </span>
              <span className="text-[0.6875rem] text-slate-500">
                {formatFileSize(attachment.file.size)}
              </span>
            </span>
          </div>
          <button
            aria-label={`Quitar ${attachment.file.name}`}
            className="ui-pressable grid size-11 shrink-0 place-items-center rounded-[4px] text-slate-500 outline-none hover:bg-slate-200 hover:text-slate-900 focus-visible:ring-2 focus-visible:ring-slate-500"
            disabled={isSending}
            onClick={clearAttachment}
            type="button"
          >
            <svg aria-hidden="true" className="size-4" fill="none" viewBox="0 0 20 20">
              <path d="m5 5 10 10M15 5 5 15" stroke="currentColor" strokeLinecap="round" strokeWidth="1.6" />
            </svg>
          </button>
        </div>
      ) : null}

      <label className="sr-only" htmlFor="whatsapp-message-composer">
        Mensaje
      </label>
      <textarea
        aria-describedby={describedBy}
        className="ui-field min-h-20 resize-y text-sm leading-5"
        disabled={Boolean(backendDisabledReason) || isSending}
        id="whatsapp-message-composer"
        onChange={(event) => setBody(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Escribí una respuesta…"
        rows={2}
        value={body}
      />
      <p
        className={[
          'mt-1.5 text-xs leading-5',
          disabledReason ? 'font-medium text-amber-800' : 'text-slate-500',
        ].join(' ')}
        id={helpId}
      >
        {disabledReason ?? 'Enter para enviar · Shift+Enter para una nueva línea'}
      </p>
      {sendError || fileError ? (
        <div className="mt-2 flex flex-wrap items-center justify-between gap-2" id={errorId} role="alert">
          <p className="text-xs font-medium text-rose-700">
            {sendError ?? fileError}
          </p>
          {hasFailedSend ? (
            <span className="flex gap-2">
              <Button
                disabled={isSending}
                onClick={() => void retry()}
                size="compact"
              >
                Reintentar mismo envío
              </Button>
              <Button
                disabled={isSending}
                onClick={onDiscardFailed}
                size="compact"
                variant="ghost"
              >
                Descartar intento
              </Button>
            </span>
          ) : null}
        </div>
      ) : null}

      <div className="mt-2 flex items-center justify-between gap-3">
        <label
          className={buttonClassName({
            size: 'compact',
            variant: 'ghost',
            className:
              disabledReason || attachment
                ? 'pointer-events-none opacity-45'
                : 'cursor-pointer focus-within:ring-2 focus-within:ring-slate-500 focus-within:ring-offset-2',
          })}
        >
          <svg aria-hidden="true" className="size-4" fill="none" viewBox="0 0 20 20">
            <path d="m6 10.5 4.8-4.8a2.3 2.3 0 1 1 3.2 3.2l-6 6a3.5 3.5 0 0 1-5-5l6.4-6.4" stroke="currentColor" strokeLinecap="round" strokeWidth="1.5" />
          </svg>
          Adjuntar imagen o PDF
          <input
            accept="image/jpeg,image/png,image/webp,application/pdf"
            className="sr-only"
            disabled={Boolean(disabledReason) || Boolean(attachment)}
            onChange={(event) => handleFile(event.target.files?.[0])}
            ref={fileInputRef}
            type="file"
          />
        </label>
        <Button
          disabled={!canSend}
          size="compact"
          type="submit"
          variant="primary"
        >
          {isSending ? 'Enviando…' : 'Enviar'}
        </Button>
      </div>
    </form>
  )
}
