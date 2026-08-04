import { useEffect, useState, type FormEvent } from 'react'

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
      title="Marcar como perdida"
    >
      <form aria-busy={isSubmitting} onSubmit={handleSubmit}>
        <div className="space-y-4 px-5 py-5">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-800" htmlFor="loss-reason">
              Motivo
            </label>
            <select
              aria-describedby={error ? 'loss-reason-error' : undefined}
              aria-invalid={Boolean(error)}
              autoFocus
              className="min-h-11 w-full border border-slate-300 bg-white px-3 py-2 text-base outline-none focus:border-red-600 focus:ring-2 focus:ring-red-200"
              disabled={isSubmitting}
              id="loss-reason"
              onChange={(event) => {
                setLossReason(event.target.value as LossReason | '')
                setError(null)
              }}
              value={lossReason}
            >
              <option value="">Seleccionar motivo</option>
              {LOSS_REASON_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            {error ? (
              <p className="mt-2 text-sm font-medium text-red-700" id="loss-reason-error" role="alert">
                {error}
              </p>
            ) : null}
          </div>
        </div>

        <footer className="flex flex-col-reverse gap-2 border-t border-slate-200 px-5 py-4 sm:flex-row sm:justify-end">
          <button
            className="min-h-11 border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-amber-500 disabled:opacity-40"
            disabled={isSubmitting}
            onClick={onClose}
            type="button"
          >
            Cancelar
          </button>
          <button
            className="min-h-11 bg-red-700 px-4 py-2 text-sm font-bold text-white outline-none hover:bg-red-800 focus-visible:ring-2 focus-visible:ring-red-600 focus-visible:ring-offset-2 disabled:cursor-wait disabled:bg-red-300"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? 'Guardando…' : 'Confirmar pérdida'}
          </button>
        </footer>
      </form>
    </Modal>
  )
}
