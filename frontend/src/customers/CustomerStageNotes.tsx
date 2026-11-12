import { useEffect, useState } from 'react'
import { apiRequest } from '../api/client'
import type { ApiSession } from '../api/opportunities'
import { OPPORTUNITY_STATUS_LABELS } from '../pipeline/config'
import type { OpportunityStatusHistory, PaginatedResponse } from '../pipeline/types'
import { AppLink } from '../routing/router'
import { Button } from '../shared/Button'
import { formatDateTime } from '../shared/formatters'

type StageNote = OpportunityStatusHistory & { opportunity_id: number; author_name: string | null }

export function CustomerStageNotes({
  customerId,
  session,
}: {
  customerId: number
  session: ApiSession
}) {
  const [result, setResult] = useState<PaginatedResponse<StageNote> | null>(null)
  const [page, setPage] = useState(1)
  const [retry, setRetry] = useState(0)
  const [error, setError] = useState(false)
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    void retry
    const controller = new AbortController()
    setLoading(true)
    setError(false)
    apiRequest<PaginatedResponse<StageNote>>(
      `/customers/${customerId}/stage-notes?page=${page}&page_size=20`,
      { ...session, signal: controller.signal },
    )
      .then((data) => {
        if (!controller.signal.aborted) setResult(data)
      })
      .catch(() => {
        if (!controller.signal.aborted) setError(true)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [customerId, page, session, retry])
  return (
    <section
      aria-labelledby='customer-stage-notes-title'
      className='ui-panel mt-4 space-y-4 px-5 py-5 sm:px-6'
    >
      <h3 className='text-base font-semibold' id='customer-stage-notes-title'>
        Notas de cambios de estado
      </h3>
      <p className='text-sm text-[var(--text-secondary)]'>
        Seguimiento de todas las oportunidades de este cliente.
      </p>
      {loading ? (
        <p role='status'>Cargando notas…</p>
      ) : error ? (
        <div role='alert'>
          No pudimos cargar las notas.{' '}
          <Button onClick={() => setRetry((value) => value + 1)}>Reintentar</Button>
        </div>
      ) : result?.items.length ? (
        <>
          <ol className='space-y-4'>
            {result.items.map((entry) => (
              <li className='border-t border-[var(--divider)] pt-4' key={entry.id}>
                <div className='flex flex-wrap justify-between gap-2 text-xs text-[var(--text-secondary)]'>
                  <span>
                    {entry.from_status ? `${OPPORTUNITY_STATUS_LABELS[entry.from_status]} → ` : ''}
                    {OPPORTUNITY_STATUS_LABELS[entry.to_status]} · {entry.author_name ?? 'Sistema'}
                  </span>
                  <time dateTime={entry.changed_at}>{formatDateTime(entry.changed_at)}</time>
                </div>
                <p className='my-2 whitespace-pre-wrap break-words text-sm leading-6 [overflow-wrap:anywhere]'>
                  {entry.note}
                </p>
                <AppLink
                  className='text-sm font-semibold underline'
                  origin={{ kind: 'customer', customerId }}
                  to={{
                    kind: 'opportunity',
                    opportunityId: entry.opportunity_id,
                    surface: 'pipeline',
                  }}
                >
                  Ver oportunidad #{entry.opportunity_id}
                </AppLink>
              </li>
            ))}
          </ol>
          <div className='flex flex-wrap items-center justify-between gap-2 text-sm'>
            <span>
              {(page - 1) * 20 + 1}–{Math.min(page * 20, result.total)} de {result.total} notas
            </span>
            <div className='flex gap-2'>
              <Button disabled={page === 1} onClick={() => setPage((value) => value - 1)}>
                Anterior
              </Button>
              <Button
                disabled={page * 20 >= result.total}
                onClick={() => setPage((value) => value + 1)}
              >
                Siguiente
              </Button>
            </div>
          </div>
        </>
      ) : (
        <p className='text-sm text-[var(--text-secondary)]'>
          Todavía no hay notas de cambios de estado para este cliente.
        </p>
      )}
    </section>
  )
}
