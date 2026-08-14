import { type ChangeEvent, useMemo, useState } from 'react'

import { commitCustomerImport, dryRunCustomerImport, getCustomerImport } from '../api/customers'
import type { ApiSession } from '../api/opportunities'
import { Button } from '../shared/Button'
import { InlineFeedback } from '../shared/InlineFeedback'
import { Modal } from '../shared/Modal'
import type { CustomerImportReport } from './types'

type ImportStep = 'choose' | 'review' | 'result'

function importErrorMessage(error: unknown, operation: 'validate' | 'commit'): string {
  if (error instanceof Error && error.name === 'ApiError') {
    return operation === 'validate'
      ? 'No pudimos validar el archivo. Revisá el CSV e intentá nuevamente.'
      : 'No pudimos confirmar la importación. Tus clientes no fueron importados parcialmente.'
  }
  return operation === 'validate'
    ? 'No pudimos validar el archivo. Revisá la conexión e intentá nuevamente.'
    : 'No pudimos confirmar la importación. Tus clientes no fueron importados parcialmente.'
}

function ImportSummary({ report }: { report: CustomerImportReport }) {
  return (
    <dl className='grid grid-cols-2 gap-2 text-sm sm:grid-cols-4'>
      <div className='rounded-[var(--radius-control)] bg-[var(--surface-subtle)] px-3 py-2'>
        <dt className='text-xs text-[var(--text-secondary)]'>Crear</dt>
        <dd className='mt-0.5 font-semibold tabular-nums'>{report.create_count}</dd>
      </div>
      <div className='rounded-[var(--radius-control)] bg-[var(--surface-subtle)] px-3 py-2'>
        <dt className='text-xs text-[var(--text-secondary)]'>Completar</dt>
        <dd className='mt-0.5 font-semibold tabular-nums'>{report.enrich_count}</dd>
      </div>
      <div className='rounded-[var(--radius-control)] bg-[var(--surface-subtle)] px-3 py-2'>
        <dt className='text-xs text-[var(--text-secondary)]'>Sin cambios</dt>
        <dd className='mt-0.5 font-semibold tabular-nums'>{report.unchanged_count}</dd>
      </div>
      <div className='rounded-[var(--radius-control)] bg-[var(--destructive-subtle)] px-3 py-2'>
        <dt className='text-xs text-[var(--destructive-text)]'>Con errores</dt>
        <dd className='mt-0.5 font-semibold tabular-nums text-[var(--destructive-text)]'>
          {report.error_count}
        </dd>
      </div>
    </dl>
  )
}

function ImportIssues({ report }: { report: CustomerImportReport }) {
  const issueRows = report.rows.filter((row) => row.issues.length > 0)
  if (issueRows.length === 0) return null
  return (
    <section aria-labelledby='import-issues-title' className='mt-4'>
      <h3 className='text-sm font-semibold' id='import-issues-title'>
        Filas que requieren corrección
      </h3>
      <div className='mt-2 max-h-48 overflow-y-auto rounded-[var(--radius-control)] border border-[var(--destructive-border)]'>
        <ul className='divide-y divide-[var(--border-subtle)] text-sm'>
          {issueRows.map((row) => (
            <li className='px-3 py-2.5' key={row.row_number}>
              <p className='font-medium'>
                Fila {row.row_number}
                {row.name ? ` · ${row.name}` : ''}
              </p>
              {row.issues.map((issue) => (
                <p
                  className='mt-1 text-[var(--destructive-text)]'
                  key={`${issue.code}-${issue.field_name ?? ''}-${issue.message}`}
                >
                  {issue.field_name ? `${issue.field_name}: ` : ''}
                  {issue.message}
                </p>
              ))}
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}

export function CustomerImportModal({
  isOpen,
  onClose,
  onCommitted,
  session,
}: {
  isOpen: boolean
  onClose: () => void
  onCommitted: (report: CustomerImportReport) => void
  session: ApiSession
}) {
  const [file, setFile] = useState<File | null>(null)
  const [report, setReport] = useState<CustomerImportReport | null>(null)
  const [step, setStep] = useState<ImportStep>('choose')
  const [isPending, setIsPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isDiscarding, setIsDiscarding] = useState(false)
  const canCommit = report?.status === 'VALID' && report.error_count === 0
  const title =
    step === 'choose'
      ? 'Importar clientes'
      : step === 'review'
        ? 'Revisar importación'
        : 'Importación completada'
  const selectedLabel = useMemo(() => file?.name ?? 'Ningún archivo seleccionado', [file])

  const reset = () => {
    setFile(null)
    setReport(null)
    setStep('choose')
    setIsPending(false)
    setError(null)
    setIsDiscarding(false)
  }
  const discard = () => {
    if (isPending) return
    reset()
    onClose()
  }
  const requestClose = () => {
    if (isPending) return
    if (step !== 'result' && (file || report)) {
      setIsDiscarding(true)
      setError(
        'Hay una importación en curso. Elegí “Descartar importación” para salir sin confirmarla.',
      )
      return
    }
    discard()
  }
  const chooseFile = (event: ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0] ?? null
    setFile(selected)
    setReport(null)
    setError(null)
  }
  const validate = async () => {
    if (!file) {
      setError('Elegí un archivo CSV para continuar.')
      return
    }
    setIsPending(true)
    setError(null)
    try {
      const nextReport = await dryRunCustomerImport(file, crypto.randomUUID(), session)
      setReport(nextReport)
      setStep('review')
    } catch (caught) {
      setError(importErrorMessage(caught, 'validate'))
    } finally {
      setIsPending(false)
    }
  }
  const commit = async () => {
    if (!report || !canCommit) return
    setIsPending(true)
    setError(null)
    try {
      const result = await commitCustomerImport(report, crypto.randomUUID(), session)
      const committed = { ...report, status: result.status, committed_at: result.committed_at }
      setReport(committed)
      setStep('result')
      onCommitted(committed)
    } catch (caught) {
      try {
        const refreshed = await getCustomerImport(report.id, session)
        setReport(refreshed)
        if (refreshed.status === 'COMMITTED') {
          setStep('result')
          onCommitted(refreshed)
        } else {
          setError(importErrorMessage(caught, 'commit'))
        }
      } catch {
        setError(importErrorMessage(caught, 'commit'))
      }
    } finally {
      setIsPending(false)
    }
  }

  return (
    <Modal
      closeDisabled={isPending}
      description='La validación no modifica clientes. La confirmación importa todas las filas válidas o ninguna.'
      isOpen={isOpen}
      onClose={requestClose}
      title={title}
    >
      <div className='max-h-[65dvh] space-y-4 overflow-y-auto px-5 py-5'>
        {error ? <InlineFeedback message={error} /> : null}
        {step === 'choose' ? (
          <>
            <div>
              <label className='ui-label' htmlFor='customer-import-file'>
                Archivo CSV
              </label>
              <input
                accept='.csv,text/csv'
                className='block w-full text-sm text-[var(--text-secondary)] file:mr-3 file:rounded-[var(--radius-control)] file:border-0 file:bg-[var(--surface-subtle)] file:px-3 file:py-2 file:font-medium file:text-[var(--text-primary)]'
                data-modal-initial-focus
                disabled={isPending}
                id='customer-import-file'
                onChange={chooseFile}
                type='file'
              />
              <p className='mt-2 text-sm text-[var(--text-secondary)]'>
                Columnas aceptadas: <code>name,company,email,phone,province</code>. {selectedLabel}
              </p>
            </div>
            <p className='text-sm leading-6 text-[var(--text-secondary)]'>
              Primero revisaremos el archivo completo. No se creará ni actualizará ningún cliente en
              este paso.
            </p>
          </>
        ) : report ? (
          <>
            <p className='text-sm text-[var(--text-secondary)]'>
              {report.source_filename} · {report.row_count}{' '}
              {report.row_count === 1 ? 'fila' : 'filas'}
            </p>
            <ImportSummary report={report} />
            <ImportIssues report={report} />
            {step === 'review' ? (
              <p className='rounded-[var(--radius-control)] border border-[var(--border-default)] bg-[var(--surface-subtle)] px-3 py-2.5 text-sm leading-6'>
                {canCommit
                  ? 'Al confirmar, FAA importará todos los cambios listados de forma atómica. Si algo falla, no se importará ninguna fila.'
                  : 'Corregí las filas indicadas y volvés a validar el CSV. Esta previsualización no se puede confirmar.'}
              </p>
            ) : (
              <p className='text-sm leading-6 text-[var(--text-secondary)]'>
                La importación se completó de forma atómica. No hubo importaciones parciales.
              </p>
            )}
          </>
        ) : null}
      </div>
      <footer className='flex flex-wrap justify-end gap-3 border-t border-[var(--border-default)] px-5 py-4'>
        {step === 'review' ? (
          <Button
            disabled={isPending}
            onClick={() => {
              setStep('choose')
              setReport(null)
              setError(null)
            }}
          >
            Elegir otro CSV
          </Button>
        ) : null}
        <Button disabled={isPending} onClick={isDiscarding ? discard : requestClose}>
          {step === 'result' ? 'Cerrar' : isDiscarding ? 'Descartar importación' : 'Cancelar'}
        </Button>
        {step === 'choose' ? (
          <Button disabled={isPending} onClick={() => void validate()} variant='primary'>
            {isPending ? 'Validando…' : 'Validar archivo'}
          </Button>
        ) : null}
        {step === 'review' && canCommit ? (
          <Button disabled={isPending} onClick={() => void commit()} variant='primary'>
            {isPending ? 'Confirmando…' : 'Confirmar importación'}
          </Button>
        ) : null}
      </footer>
    </Modal>
  )
}
