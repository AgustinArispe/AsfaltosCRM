import { type FormEvent, useEffect, useId, useRef, useState } from 'react'
import { ApiError } from '../api/client'
import {
  archiveCustomerNote,
  createCustomerNote,
  listCustomerNotes,
  updateCustomerNote,
} from '../api/customers'
import type { ApiSession } from '../api/opportunities'
import type { PaginatedResponse } from '../pipeline/types'
import { Button } from '../shared/Button'
import { ConfirmationDialog } from '../shared/ConfirmationDialog'
import { formatDateTime } from '../shared/formatters'
import { CustomerNoteField } from './CustomerNoteField'
import { CUSTOMER_NOTES_CHANGED, notifyCustomerNotesChanged } from './customer-notes-events'
import type { CustomerNote } from './types'

export function CustomerNotes({
  customerId,
  session,
  compact = false,
}: {
  customerId: number
  session: ApiSession
  compact?: boolean
}) {
  const titleId = useId()
  const [result, setResult] = useState<PaginatedResponse<CustomerNote> | null>(null)
  const [page, setPage] = useState(1)
  const [refresh, setRefresh] = useState(0)
  const [loadState, setLoadState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [editing, setEditing] = useState<CustomerNote | 'new' | null>(null)
  const [archiving, setArchiving] = useState<CustomerNote | null>(null)
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const editorRef = useRef<HTMLTextAreaElement>(null)
  const commandRef = useRef<{ id: string; body: string } | null>(null)
  const pageSize = compact ? 3 : 10

  useEffect(() => {
    if (editing) editorRef.current?.focus({ preventScroll: true })
  }, [editing])

  useEffect(() => {
    const listener = (event: Event) => {
      if (event instanceof CustomEvent && event.detail === customerId) {
        setRefresh((current) => current + 1)
      }
    }
    window.addEventListener(CUSTOMER_NOTES_CHANGED, listener)
    return () => window.removeEventListener(CUSTOMER_NOTES_CHANGED, listener)
  }, [customerId])

  useEffect(() => {
    void refresh
    const controller = new AbortController()
    setLoadState('loading')
    listCustomerNotes(customerId, page, pageSize, { ...session, signal: controller.signal })
      .then((data) => {
        if (controller.signal.aborted) return
        if (page > 1 && data.items.length === 0) {
          setPage(Math.max(1, Math.ceil(data.total / pageSize)))
          return
        }
        setResult(data)
        setLoadState('ready')
      })
      .catch(() => {
        if (!controller.signal.aborted) setLoadState('error')
      })
    return () => controller.abort()
  }, [customerId, page, pageSize, refresh, session])

  const mutate = async (action: () => Promise<unknown>, onSaved: () => void) => {
    if (busy) return
    setBusy(true)
    setError(null)
    try {
      await action()
      onSaved()
      notifyCustomerNotesChanged(customerId)
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 409) {
        setError('La nota cambió o ya hay tres notas fijadas. Revisá la ficha e intentá de nuevo.')
        notifyCustomerNotesChanged(customerId)
      } else {
        setError('No pudimos guardar el cambio. Intentá de nuevo.')
      }
    } finally {
      setBusy(false)
    }
  }

  const edit = (note: CustomerNote | 'new') => {
    setError(null)
    setEditing(note)
    setDraft(note === 'new' ? '' : note.body)
    commandRef.current = null
  }

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const body = draft.trim()
    if (!editing || !body) return
    const saved = () => {
      if (editing === 'new') setPage(1)
      setEditing(null)
      setDraft('')
    }
    if (editing !== 'new') {
      await mutate(
        () => updateCustomerNote(customerId, editing, body, editing.pinned, session),
        saved,
      )
      return
    }
    if (commandRef.current?.body !== body) commandRef.current = { id: crypto.randomUUID(), body }
    const commandId = commandRef.current.id
    await mutate(() => createCustomerNote(customerId, body, commandId, session), saved)
  }

  return (
    <section
      aria-labelledby={titleId}
      className={compact ? 'mt-5 space-y-2' : 'ui-panel mt-4 space-y-3 px-5 py-5 sm:px-6'}
    >
      <div className='flex flex-wrap items-center justify-between gap-2'>
        <h3 className={compact ? 'text-sm font-semibold' : 'text-base font-semibold'} id={titleId}>
          Para recordar
        </h3>
        {editing === null ? (
          <Button disabled={busy} onClick={() => edit('new')} size='compact' variant='secondary'>
            Agregar nota del cliente
          </Button>
        ) : null}
      </div>
      {error && !archiving ? (
        <p role='alert' className='text-sm text-[var(--destructive-text)]'>
          {error}
        </p>
      ) : null}
      {editing !== null ? (
        <form className='space-y-3' onSubmit={(event) => void save(event)}>
          <CustomerNoteField
            value={draft}
            onChange={setDraft}
            disabled={busy}
            inputRef={editorRef}
          />
          <div className='flex flex-wrap justify-end gap-2'>
            <Button
              disabled={busy}
              onClick={() => {
                setEditing(null)
                setError(null)
              }}
              size='compact'
              variant='ghost'
            >
              Cancelar
            </Button>
            <Button disabled={!draft.trim()} isLoading={busy} size='compact' type='submit'>
              Guardar nota
            </Button>
          </div>
        </form>
      ) : null}
      {loadState === 'error' ? (
        <div className='flex flex-wrap items-center gap-2 text-sm'>
          <p>No pudimos cargar las notas del cliente.</p>
          <Button
            onClick={() => setRefresh((current) => current + 1)}
            size='compact'
            variant='ghost'
          >
            Reintentar notas
          </Button>
        </div>
      ) : loadState === 'loading' && !result ? (
        <p className='text-sm text-[var(--text-secondary)]' role='status'>
          Cargando notas del cliente…
        </p>
      ) : result?.items.length ? (
        <ul className='divide-y divide-[var(--divider)]'>
          {result.items.map((note) => (
            <li key={note.id} className='space-y-1 py-2.5'>
              <p className='whitespace-pre-wrap break-words text-sm leading-5 [overflow-wrap:anywhere]'>
                {note.body}
              </p>
              <p className='text-xs text-[var(--text-secondary)]'>
                {note.pinned ? 'Fijada · ' : ''}
                {note.author_name} ·{' '}
                <time dateTime={note.created_at}>{formatDateTime(note.created_at)}</time>
              </p>
              {!compact ? (
                <div className='flex flex-wrap gap-1'>
                  <Button
                    disabled={busy || editing !== null}
                    onClick={() => edit(note)}
                    size='compact'
                    variant='ghost'
                  >
                    Editar nota
                  </Button>
                  <Button
                    disabled={busy || editing !== null}
                    onClick={() =>
                      void mutate(
                        () =>
                          updateCustomerNote(customerId, note, note.body, !note.pinned, session),
                        () => setPage(1),
                      )
                    }
                    size='compact'
                    variant='ghost'
                  >
                    {note.pinned ? 'Desfijar' : 'Fijar'}
                  </Button>
                  <Button
                    disabled={busy || editing !== null}
                    onClick={() => {
                      setError(null)
                      setArchiving(note)
                    }}
                    size='compact'
                    variant='ghost'
                  >
                    Archivar
                  </Button>
                </div>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className='text-sm text-[var(--text-secondary)]'>Todavía no hay datos para recordar.</p>
      )}
      {!compact && result && result.total > pageSize ? (
        <div className='flex justify-end gap-2'>
          <Button
            disabled={page <= 1 || loadState === 'loading'}
            onClick={() => setPage(page - 1)}
            size='compact'
            variant='secondary'
          >
            Anterior
          </Button>
          <Button
            disabled={page * pageSize >= result.total || loadState === 'loading'}
            onClick={() => setPage(page + 1)}
            size='compact'
            variant='secondary'
          >
            Siguiente
          </Button>
        </div>
      ) : null}
      {compact && result && result.total > pageSize ? (
        <p className='text-xs text-[var(--text-secondary)]'>
          Abrí la ficha para ver todas las notas.
        </p>
      ) : null}
      {archiving ? (
        <ConfirmationDialog
          isOpen
          isPending={busy}
          error={error}
          title='Archivar nota del cliente'
          confirmLabel='Archivar nota'
          pendingLabel='Archivando…'
          onCancel={() => {
            setArchiving(null)
            setError(null)
          }}
          onConfirm={() =>
            void mutate(
              () => archiveCustomerNote(customerId, archiving.id, session),
              () => setArchiving(null),
            )
          }
        >
          <p className='text-sm text-[var(--text-secondary)]'>
            La nota dejará de aparecer en Para recordar.
          </p>
        </ConfirmationDialog>
      ) : null}
    </section>
  )
}
