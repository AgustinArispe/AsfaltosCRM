import { useEffect, useState } from 'react'
import { ConfirmationDialog } from '../shared/ConfirmationDialog'
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
        caughtError instanceof Error ? caughtError.message : 'No pudimos eliminar el cliente.',
      )
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <ConfirmationDialog
      confirmLabel='Eliminar cliente'
      description='El cliente dejará de aparecer en el CRM, pero su historial comercial se conservará.'
      error={error}
      isOpen={Boolean(customer)}
      isPending={isDeleting}
      onCancel={onClose}
      onConfirm={() => void handleConfirm()}
      pendingLabel='Eliminando…'
      title={customer ? `¿Eliminar a ${customer.name}?` : 'Eliminar cliente'}
      variant='danger'
    >
      <p className='text-sm leading-6 text-slate-700'>
        Esta acción realiza un borrado lógico y no elimina sus oportunidades.
      </p>
    </ConfirmationDialog>
  )
}
