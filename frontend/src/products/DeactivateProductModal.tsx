import { useEffect, useState } from 'react'

import { InlineFeedback } from '../shared/InlineFeedback'
import { Modal } from '../shared/Modal'
import { Button } from '../shared/Button'
import type { Product } from './types'

export function DeactivateProductModal({
  product,
  onClose,
  onConfirm,
}: {
  product: Product | null
  onClose: () => void
  onConfirm: () => Promise<void>
}) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!product) return
    setError(null)
    setIsSubmitting(false)
  }, [product])

  const handleConfirm = async () => {
    setIsSubmitting(true)
    setError(null)
    try {
      await onConfirm()
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'No pudimos desactivar el producto.',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Modal
      closeDisabled={isSubmitting}
      description="El producto dejará de estar disponible para nuevas cotizaciones, pero continuará apareciendo en el historial comercial."
      isOpen={product !== null}
      onClose={onClose}
      title={product ? `¿Desactivar ${product.name}?` : 'Desactivar producto'}
    >
      <div className="px-5 py-5">
        {error ? <InlineFeedback message={error} /> : null}
        <p className="text-sm leading-6 text-slate-700">
          Podrás reactivarlo posteriormente desde este listado.
        </p>
      </div>
      <footer className="flex flex-wrap justify-end gap-3 border-t border-slate-200 px-5 py-4">
        <Button
          autoFocus
          data-modal-initial-focus
          disabled={isSubmitting}
          onClick={onClose}
        >
          Cancelar
        </Button>
        <Button
          disabled={isSubmitting}
          onClick={() => void handleConfirm()}
          variant="danger"
        >
          {isSubmitting ? 'Desactivando…' : 'Desactivar producto'}
        </Button>
      </footer>
    </Modal>
  )
}
