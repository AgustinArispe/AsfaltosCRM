import { type KeyboardEvent, useCallback, useEffect, useState } from 'react'

import { type ApiSession, createOpportunityNote, listOpportunityNotes } from '../api/opportunities'
import { Button } from '../shared/Button'
import { formatDateTime } from '../shared/formatters'
import { SegmentedControl } from '../shared/SegmentedControl'
import { InlineFeedback } from '../shared/StatusStates'
import { OPPORTUNITY_STATUS_LABELS } from './config'
import type { OpportunityDetail, OpportunityNote, OpportunityStatusHistory } from './types'

function historyDescription(entry: OpportunityStatusHistory): string {
  if (entry.from_status === null && entry.to_status === 'NUEVA') return 'Consulta creada'
  return `Pasó de ${entry.from_status ? OPPORTUNITY_STATUS_LABELS[entry.from_status] : 'sin estado'} a ${OPPORTUNITY_STATUS_LABELS[entry.to_status]}`
}

function NoteList({ notes }: { notes: readonly OpportunityNote[] }) {
  if (notes.length === 0) {
    return <p className='mt-3 text-sm text-[var(--text-secondary)]'>Aún no hay notas.</p>
  }
  return (
    <ol className='mt-3 space-y-3' aria-label='Notas de la oportunidad'>
      {notes.map((note) => (
        <li className='border-b border-[var(--border-subtle)] pb-3 last:border-0' key={note.id}>
          <p className='whitespace-pre-wrap text-sm leading-5 text-[var(--text-primary)]'>
            {note.current_revision.body}
          </p>
          <p className='mt-1 text-xs text-[var(--text-secondary)]'>
            {note.current_revision.is_pinned ? 'Nota fijada · ' : ''}
            {note.author_name} ·{' '}
            <time dateTime={note.current_revision.created_at}>
              {formatDateTime(note.current_revision.created_at)}
            </time>
          </p>
        </li>
      ))}
    </ol>
  )
}

export function OpportunityContextPanel({
  opportunity,
  session,
}: {
  opportunity: OpportunityDetail
  session: ApiSession
}) {
  const [view, setView] = useState<'activity' | 'notes'>('activity')
  const [notes, setNotes] = useState<OpportunityNote[] | null>(null)
  const [notesError, setNotesError] = useState<string | null>(null)
  const [isLoadingNotes, setIsLoadingNotes] = useState(false)
  const [draft, setDraft] = useState('')
  const [commandId, setCommandId] = useState<string | null>(null)
  const [noteError, setNoteError] = useState<string | null>(null)
  const [isSavingNote, setIsSavingNote] = useState(false)

  const loadNotes = useCallback(() => {
    setIsLoadingNotes(true)
    setNotesError(null)
    listOpportunityNotes(opportunity.id, session)
      .then((page) => setNotes(page.items))
      .catch(() => setNotesError('No pudimos cargar las notas. Intentá nuevamente.'))
      .finally(() => setIsLoadingNotes(false))
  }, [opportunity.id, session])

  useEffect(() => {
    if (view === 'notes' && notes === null && !notesError && !isLoadingNotes) loadNotes()
  }, [isLoadingNotes, loadNotes, notes, notesError, view])

  const saveNote = async () => {
    const body = draft.trim()
    if (!body || isSavingNote) return
    const nextCommandId = commandId ?? crypto.randomUUID()
    setCommandId(nextCommandId)
    setIsSavingNote(true)
    setNoteError(null)
    try {
      const saved = await createOpportunityNote(opportunity.id, body, session, nextCommandId)
      setNotes((current) => [saved, ...(current ?? []).filter((note) => note.id !== saved.id)])
      setDraft('')
      setCommandId(null)
    } catch {
      setNoteError('No pudimos guardar la nota. Revisá tu conexión e intentá nuevamente.')
    } finally {
      setIsSavingNote(false)
    }
  }

  const handleComposerKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (
      (event.ctrlKey || event.metaKey) &&
      event.key === 'Enter' &&
      !event.nativeEvent.isComposing
    ) {
      event.preventDefault()
      void saveNote()
    }
  }

  return (
    <section
      aria-labelledby={`opportunity-context-${opportunity.id}`}
      className='opportunity-detail__section px-4 py-4 sm:px-5'
    >
      <h3
        className='text-sm font-semibold text-[var(--text-primary)]'
        id={`opportunity-context-${opportunity.id}`}
      >
        Contexto
      </h3>
      <div className='mt-3'>
        <SegmentedControl
          label='Contexto de oportunidad'
          onChange={(value) => setView(value as 'activity' | 'notes')}
          segments={[
            { value: 'activity', label: 'Actividad' },
            { value: 'notes', label: 'Notas' },
          ]}
          value={view}
        />
      </div>
      {view === 'activity' ? (
        <ol className='mt-4'>
          {opportunity.history.map((entry) => (
            <li
              className='border-b border-[var(--border-subtle)] py-3 first:pt-0 last:border-0'
              key={entry.id}
            >
              <time className='text-xs text-[var(--text-secondary)]' dateTime={entry.changed_at}>
                {formatDateTime(entry.changed_at)}
              </time>
              <p className='mt-0.5 text-sm font-medium text-[var(--text-primary)]'>
                {historyDescription(entry)}
              </p>
              {entry.from_status === null ? (
                <p className='mt-0.5 text-xs text-[var(--text-secondary)]'>
                  Estado inicial: {OPPORTUNITY_STATUS_LABELS[entry.to_status]}
                </p>
              ) : null}
            </li>
          ))}
        </ol>
      ) : (
        <div className='mt-4'>
          {notesError ? (
            <div className='space-y-2'>
              <InlineFeedback message={notesError} />
              <Button onClick={loadNotes} size='compact'>
                Reintentar
              </Button>
            </div>
          ) : isLoadingNotes ? (
            <p role='status' className='text-sm text-[var(--text-secondary)]'>
              Cargando notas…
            </p>
          ) : (
            <NoteList notes={notes ?? []} />
          )}
          <div className='mt-4 border-t border-[var(--border-subtle)] pt-4'>
            <label className='ui-label' htmlFor={`opportunity-note-${opportunity.id}`}>
              Agregar nota
            </label>
            <textarea
              aria-describedby={noteError ? `opportunity-note-${opportunity.id}-error` : undefined}
              aria-invalid={Boolean(noteError)}
              className='ui-field mt-1 min-h-28 resize-y text-base'
              disabled={isSavingNote}
              id={`opportunity-note-${opportunity.id}`}
              onChange={(event) => {
                setDraft(event.target.value)
                setNoteError(null)
              }}
              onKeyDown={handleComposerKeyDown}
              placeholder='Escribí una nota interna…'
              value={draft}
            />
            <p className='mt-1 text-xs text-[var(--text-secondary)]'>
              Ctrl/Cmd + Enter para guardar.
            </p>
            {noteError ? (
              <p
                className='mt-2 text-sm font-medium text-[var(--destructive-solid)]'
                id={`opportunity-note-${opportunity.id}-error`}
                role='alert'
              >
                {noteError}
              </p>
            ) : null}
            <div className='mt-3 flex justify-end'>
              <Button disabled={!draft.trim() || isSavingNote} onClick={() => void saveNote()}>
                {isSavingNote ? 'Guardando…' : 'Guardar nota'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
