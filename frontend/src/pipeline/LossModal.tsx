import { type FormEvent, useEffect, useState } from 'react'
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
  onConfirm: (lossReason: LossReason) => Promise<void>
}) {
  const [lossReason, setLossReason] = useState<LossReason | ''>('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    void opportunity?.id
    setLossReason('')
    setError(null)
    setIsSubmitting(false)
  }, [opportunity?.id])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!lossReason) {
      setError('Seleccioná un motivo de pérdida.')
      return
    }

    setIsSubmitting(true)
    setError(null)
    try {
      await onConfirm(lossReason)
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : 'No pudimos marcar la oportunidad como perdida.',
      )
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
      <form aria-busy={isSubmitting} onSubmit={handleSubmit}>
        <div className='space-y-4 px-5 py-5'>
          <div>
            <label className='ui-label' htmlFor='loss-reason'>
              Motivo
            </label>
            <select
              aria-describedby={error ? 'loss-reason-error' : undefined}
              aria-invalid={Boolean(error)}
              className='ui-field text-base'
              data-modal-initial-focus
              disabled={isSubmitting}
              id='loss-reason'
              onChange={(event) => {
                setLossReason(event.target.value as LossReason | '')
                setError(null)
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
            {error ? (
              <p
                className='mt-2 text-sm font-medium text-[var(--destructive-text)]'
                id='loss-reason-error'
                role='alert'
              >
                {error}
              </p>
            ) : null}
          </div>
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
