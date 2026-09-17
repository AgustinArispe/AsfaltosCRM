import { type FormEvent, useEffect, useRef, useState } from 'react'
import { Button } from '../shared/Button'
import { Modal } from '../shared/Modal'
import { LOSS_REASON_OPTIONS } from './config'
import type { LossReason, OpportunitySummary } from './types'

export function LossModal({
  opportunity,
  onClose,
  onConfirm,
}: {
  opportunity: OpportunitySummary | null
  onClose: () => void
  onConfirm: (lossReason: LossReason, lossReasonDetail: string | null) => Promise<void>
}) {
  const [lossReason, setLossReason] = useState<LossReason | ''>('')
  const [lossReasonDetail, setLossReasonDetail] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [errorField, setErrorField] = useState<'reason' | 'detail' | 'form' | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const detailRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    void opportunity?.id
    setLossReason('')
    setLossReasonDetail('')
    setError(null)
    setErrorField(null)
    setIsSubmitting(false)
  }, [opportunity?.id])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!lossReason) {
      setError('Seleccioná un motivo de pérdida.')
      setErrorField('reason')
      return
    }
    const normalizedDetail = lossReasonDetail.trim()
    if (lossReason === 'OTRO' && !normalizedDetail) {
      setError('Escribí el motivo de la pérdida.')
      setErrorField('detail')
      detailRef.current?.focus()
      return
    }

    setIsSubmitting(true)
    setError(null)
    setErrorField(null)
    try {
      await onConfirm(lossReason, lossReason === 'OTRO' ? normalizedDetail : null)
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : 'No pudimos marcar la oportunidad como perdida.',
      )
      setErrorField('form')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Modal
      closeDisabled={isSubmitting}
      description={
        opportunity
          ? `${opportunity.customer.name} dejará de aparecer en el pipeline principal.`
          : undefined
      }
      isOpen={Boolean(opportunity)}
      onClose={onClose}
      title='Marcar como perdida'
    >
      <form aria-busy={isSubmitting} noValidate onSubmit={handleSubmit}>
        <div className='space-y-4 px-5 py-5'>
          <div>
            <label className='ui-label' htmlFor='loss-reason'>
              Motivo
            </label>
            <select
              aria-describedby={errorField === 'reason' ? 'loss-reason-error' : undefined}
              aria-invalid={errorField === 'reason'}
              className='ui-field text-base'
              data-modal-initial-focus
              disabled={isSubmitting}
              id='loss-reason'
              onChange={(event) => {
                const reason = event.target.value as LossReason | ''
                setLossReason(reason)
                if (reason !== 'OTRO') setLossReasonDetail('')
                setError(null)
                setErrorField(null)
              }}
              value={lossReason}
            >
              <option value=''>Seleccionar motivo</option>
              {LOSS_REASON_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            {error && errorField === 'reason' ? (
              <p
                className='mt-2 text-sm font-medium text-[var(--destructive-text)]'
                id='loss-reason-error'
                role='alert'
              >
                {error}
              </p>
            ) : null}
          </div>
          {lossReason === 'OTRO' ? (
            <div>
              <label className='ui-label' htmlFor='loss-reason-detail'>
                Detalle del motivo
              </label>
              <textarea
                aria-describedby={`loss-reason-detail-help${errorField === 'detail' ? ' loss-reason-detail-error' : ''}`}
                aria-invalid={errorField === 'detail'}
                className='ui-field min-h-28 resize-y py-2.5 text-base'
                disabled={isSubmitting}
                id='loss-reason-detail'
                maxLength={500}
                onChange={(event) => {
                  setLossReasonDetail(event.target.value)
                  setError(null)
                  setErrorField(null)
                }}
                ref={detailRef}
                required
                value={lossReasonDetail}
              />
              <div
                className='mt-1 flex items-start justify-between gap-3 text-xs text-[var(--text-tertiary)]'
                id='loss-reason-detail-help'
              >
                <span>Explicá brevemente por qué se perdió la oportunidad.</span>
                <span aria-hidden='true'>{lossReasonDetail.length}/500</span>
                <span className='sr-only' aria-live='polite'>
                  {lossReasonDetail.length} de 500 caracteres
                </span>
              </div>
              {error && errorField === 'detail' ? (
                <p
                  className='mt-2 text-sm font-medium text-[var(--destructive-text)]'
                  id='loss-reason-detail-error'
                  role='alert'
                >
                  {error}
                </p>
              ) : null}
            </div>
          ) : null}
          {error && errorField === 'form' ? (
            <p className='text-sm font-medium text-[var(--destructive-text)]' role='alert'>
              {error}
            </p>
          ) : null}
        </div>

        <footer className='flex flex-col-reverse gap-2 border-t border-[var(--subtle-border)] px-5 py-4 sm:flex-row sm:justify-end'>
          <Button disabled={isSubmitting} onClick={onClose}>
            Cancelar
          </Button>
          <Button disabled={isSubmitting} type='submit' variant='danger'>
            {isSubmitting ? 'Guardando…' : 'Confirmar pérdida'}
          </Button>
        </footer>
      </form>
    </Modal>
  )
}
