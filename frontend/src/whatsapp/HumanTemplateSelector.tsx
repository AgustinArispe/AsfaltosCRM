import { type ChangeEvent, type KeyboardEvent, useEffect, useMemo, useRef, useState } from 'react'

import { Button } from '../shared/Button'
import { Modal } from '../shared/Modal'
import type {
  HumanTemplateSendInput,
  StagedWhatsAppAttachment,
  WhatsAppHumanTemplate,
} from './types'

const IMAGE_MIME_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp'])

function stageHeaderAttachment(file: File): StagedWhatsAppAttachment | null {
  if (file.size === 0) return null
  if (IMAGE_MIME_TYPES.has(file.type)) {
    return { file, messageType: 'IMAGE', previewUrl: URL.createObjectURL(file) }
  }
  if (file.type === 'application/pdf') {
    return { file, messageType: 'DOCUMENT', previewUrl: null }
  }
  return null
}

export function HumanTemplateSelector({
  isOpen,
  templates,
  status,
  error,
  isSending,
  onClose,
  onReload,
  onSend,
}: {
  isOpen: boolean
  templates: WhatsAppHumanTemplate[]
  status: 'idle' | 'loading' | 'ready' | 'error'
  error: string | null
  isSending: boolean
  onClose: () => void
  onReload: () => Promise<void>
  onSend: (input: HumanTemplateSendInput) => Promise<boolean>
}) {
  const [selected, setSelected] = useState<WhatsAppHumanTemplate | null>(null)
  const [values, setValues] = useState<Record<string, string>>({})
  const [headerAttachment, setHeaderAttachment] = useState<StagedWhatsAppAttachment | null>(null)
  const [fileError, setFileError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!isOpen) return
    void onReload()
  }, [isOpen, onReload])

  useEffect(() => {
    if (!selected) return
    setValues(Object.fromEntries(selected.parameter_names.map((name) => [name, ''])))
  }, [selected])

  useEffect(
    () => () => {
      if (headerAttachment?.previewUrl) URL.revokeObjectURL(headerAttachment.previewUrl)
    },
    [headerAttachment],
  )

  const expectsHeaderMedia =
    selected?.header_type === 'IMAGE' || selected?.header_type === 'DOCUMENT'
  const acceptedMedia =
    selected?.header_type === 'IMAGE' ? 'image/jpeg,image/png,image/webp' : 'application/pdf'
  const canSend = useMemo(
    () =>
      selected
        ? selected.parameter_names.every((name) => values[name]?.trim()) &&
          (!selected.header_media_required || Boolean(headerAttachment)) &&
          !isSending
        : false,
    [headerAttachment, isSending, selected, values],
  )

  const clearHeader = () => {
    if (headerAttachment?.previewUrl) URL.revokeObjectURL(headerAttachment.previewUrl)
    setHeaderAttachment(null)
    setFileError(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  const handleHeader = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file || !selected) return
    const attachment = stageHeaderAttachment(file)
    const expected = selected.header_type === 'IMAGE' ? 'IMAGE' : 'DOCUMENT'
    if (!attachment || attachment.messageType !== expected) {
      setFileError(
        expected === 'IMAGE'
          ? 'Seleccioná una imagen JPG, PNG o WebP para el encabezado.'
          : 'Seleccioná un PDF para el encabezado.',
      )
      event.target.value = ''
      return
    }
    clearHeader()
    setHeaderAttachment(attachment)
  }

  const preventUnsafeEnter = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') event.preventDefault()
  }

  const submit = async () => {
    if (!selected || !canSend) return
    const success = await onSend({
      template: selected,
      parameters: selected.parameter_names.map((name) => ({ name, value: values[name].trim() })),
      headerAttachment,
    })
    if (success) onClose()
  }

  return (
    <Modal
      description='Elegí una plantilla aprobada y completá únicamente los datos requeridos.'
      isOpen={isOpen}
      onClose={onClose}
      size='large'
      title='Enviar plantilla aprobada'
    >
      <form
        className='grid max-h-[min(38rem,calc(100dvh-12rem))] min-h-0 md:grid-cols-[minmax(0,1fr)_minmax(18rem,0.8fr)]'
        onSubmit={(event) => {
          event.preventDefault()
          void submit()
        }}
      >
        <section
          aria-label='Plantillas disponibles'
          className='min-h-0 overflow-y-auto border-b border-[var(--border-default)] p-4 md:border-b-0 md:border-r'
        >
          {status === 'loading' ? (
            <p className='text-sm text-[var(--text-secondary)]'>Cargando plantillas…</p>
          ) : null}
          {status === 'error' ? (
            <div>
              <p className='text-sm text-[var(--destructive)]' role='alert'>
                {error ?? 'No pudimos cargar las plantillas.'}
              </p>
              <Button className='mt-3' onClick={() => void onReload()} size='compact' type='button'>
                Reintentar
              </Button>
            </div>
          ) : null}
          {status === 'ready' && templates.length === 0 ? (
            <p className='text-sm leading-6 text-[var(--text-secondary)]'>
              No hay plantillas aprobadas disponibles para esta conversación.
            </p>
          ) : null}
          <ul className='space-y-2' aria-label='Plantillas aprobadas'>
            {templates.map((template) => {
              const isSelected =
                selected?.name === template.name && selected.language === template.language
              return (
                <li key={`${template.name}-${template.language}`}>
                  <button
                    aria-pressed={isSelected}
                    className={`ui-pressable w-full rounded-[var(--radius-control)] border p-3 text-left outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)] ${
                      isSelected
                        ? 'border-[var(--action-secondary)] bg-[var(--selection-surface)]'
                        : 'border-[var(--border-default)] bg-[var(--surface)] hover:bg-[var(--hover)]'
                    }`}
                    data-modal-initial-focus={templates[0] === template ? true : undefined}
                    onClick={() => {
                      clearHeader()
                      setSelected(template)
                    }}
                    type='button'
                  >
                    <span className='block text-sm font-semibold text-[var(--text-primary)]'>
                      {template.name}
                    </span>
                    <span className='mt-1 block text-xs text-[var(--text-secondary)]'>
                      {template.language} · {template.category}
                    </span>
                    <span className='mt-2 block text-xs leading-5 text-[var(--text-secondary)]'>
                      {template.body_preview ??
                        'El contenido se administra en la plantilla aprobada.'}
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        </section>

        <section aria-label='Datos de la plantilla' className='min-h-0 overflow-y-auto p-4'>
          {!selected ? (
            <p className='text-sm leading-6 text-[var(--text-secondary)]'>
              Seleccioná una plantilla para ver sus requisitos.
            </p>
          ) : (
            <>
              <p className='text-sm font-semibold text-[var(--text-primary)]'>{selected.name}</p>
              <p className='mt-1 text-xs text-[var(--text-secondary)]'>
                {selected.parameter_names.length > 0
                  ? 'Completá los campos requeridos.'
                  : 'Esta plantilla no requiere campos adicionales.'}
              </p>
              <div className='mt-4 space-y-3'>
                {selected.parameter_names.map((name) => (
                  <label
                    className='block text-sm font-medium text-[var(--text-primary)]'
                    key={name}
                  >
                    {name}
                    <input
                      className='ui-field mt-1'
                      onChange={(event) =>
                        setValues((current) => ({ ...current, [name]: event.target.value }))
                      }
                      onKeyDown={preventUnsafeEnter}
                      required
                      value={values[name] ?? ''}
                    />
                  </label>
                ))}
              </div>
              {expectsHeaderMedia ? (
                <div className='mt-4 rounded-[var(--radius-control)] border border-[var(--border-default)] p-3'>
                  <p className='text-sm font-medium text-[var(--text-primary)]'>
                    Encabezado {selected.header_media_required ? 'requerido' : 'opcional'}
                  </p>
                  {headerAttachment ? (
                    <div className='mt-2 flex items-center gap-3'>
                      {headerAttachment.previewUrl ? (
                        <img
                          alt={`Vista previa de ${headerAttachment.file.name}`}
                          className='size-12 rounded object-cover'
                          src={headerAttachment.previewUrl}
                        />
                      ) : null}
                      <span className='min-w-0 flex-1 truncate text-xs text-[var(--text-secondary)]'>
                        {headerAttachment.file.name}
                      </span>
                      <Button onClick={clearHeader} size='compact' type='button' variant='ghost'>
                        Quitar
                      </Button>
                    </div>
                  ) : (
                    <label className='mt-2 inline-flex min-h-11 cursor-pointer items-center text-xs font-semibold text-[var(--text-link)]'>
                      Adjuntar {selected.header_type === 'IMAGE' ? 'imagen' : 'PDF'}
                      <input
                        accept={acceptedMedia}
                        className='sr-only'
                        onChange={handleHeader}
                        ref={inputRef}
                        type='file'
                      />
                    </label>
                  )}
                  {fileError ? (
                    <p className='mt-2 text-xs font-medium text-[var(--destructive)]' role='alert'>
                      {fileError}
                    </p>
                  ) : null}
                </div>
              ) : null}
            </>
          )}
          <div className='mt-6 flex justify-end gap-2'>
            <Button onClick={onClose} size='compact' type='button' variant='ghost'>
              Cancelar
            </Button>
            <Button disabled={!canSend} size='compact' type='submit' variant='primary'>
              {isSending ? 'Enviando…' : 'Enviar plantilla'}
            </Button>
          </div>
        </section>
      </form>
    </Modal>
  )
}
