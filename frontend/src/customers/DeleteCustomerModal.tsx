import { useEffect, useState } from 'react'

import { InlineFeedback } from '../shared/InlineFeedback'
import { Modal } from '../shared/Modal'
import { Button } from '../shared/Button'
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
        <Button
          autoFocus
          data-modal-initial-focus
          disabled={isDeleting}
          onClick={onClose}
        >
          Cancelar
        </Button>
        <Button
          disabled={isDeleting}
          onClick={() => void handleConfirm()}
          variant="danger"
        >
          {isDeleting ? 'Eliminando…' : 'Eliminar cliente'}
        </Button>
      </footer>
    </Modal>
  )
}
