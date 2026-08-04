import { useEffect, useState } from 'react'

import { InlineFeedback } from '../shared/InlineFeedback'
import { Modal } from '../shared/Modal'
import type { CustomerSummary } from './types'

export function DeleteCustomerModal({
  customer,
  onClose,
  onConfirm,
}: {
  customer: CustomerSummary | null
  onClose: () => void
  onConfirm: () => Promise<void>
}) {
  const [isDeleting, setIsDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (customer) setError(null)
  }, [customer])

  const handleConfirm = async () => {
    setIsDeleting(true)
    setError(null)
    try {
      await onConfirm()
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'No pudimos eliminar el cliente.',
      )
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <Modal
      closeDisabled={isDeleting}
      description="El cliente dejará de aparecer en el CRM, pero su historial comercial se conservará."
      isOpen={customer !== null}
      onClose={onClose}
      title={customer ? `¿Eliminar a ${customer.name}?` : 'Eliminar cliente'}
    >
      <div className="px-5 py-5">
        {error ? <InlineFeedback message={error} /> : null}
        <p className="text-sm leading-6 text-slate-700">
          Esta acción realiza un borrado lógico y no elimina sus oportunidades.
        </p>
      </div>
      <footer className="flex flex-wrap justify-end gap-3 border-t border-slate-200 px-5 py-4">
        <button
          autoFocus
          className="min-h-11 border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-amber-500 disabled:cursor-not-allowed disabled:opacity-50"
          data-modal-initial-focus
          disabled={isDeleting}
          onClick={onClose}
          type="button"
        >
          Cancelar
        </button>
        <button
          className="min-h-11 bg-red-700 px-4 py-2 text-sm font-bold text-white outline-none hover:bg-red-600 focus-visible:ring-2 focus-visible:ring-red-600 focus-visible:ring-offset-2 disabled:cursor-wait disabled:opacity-50"
          disabled={isDeleting}
          onClick={() => void handleConfirm()}
          type="button"
        >
          {isDeleting ? 'Eliminando…' : 'Eliminar cliente'}
        </button>
      </footer>
    </Modal>
  )
}
