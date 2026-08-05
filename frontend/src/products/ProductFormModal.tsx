import { useEffect, useId, useRef, useState, type FormEvent } from 'react'

import { InlineFeedback } from '../shared/InlineFeedback'
import { Modal } from '../shared/Modal'
import type { Product } from './types'

export function ProductFormModal({
  isOpen,
  product,
  onClose,
  onSubmit,
}: {
  isOpen: boolean
  product: Product | null
  onClose: () => void
  onSubmit: (name: string) => Promise<void>
}) {
  const [name, setName] = useState('')
  const [nameError, setNameError] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const nameInputRef = useRef<HTMLInputElement>(null)
  const formId = useId()
  const isEditing = product !== null

  useEffect(() => {
    if (!isOpen) return
    setName(product?.name ?? '')
    setNameError(null)
    setSubmitError(null)
    setIsSubmitting(false)
  }, [isOpen, product])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const trimmedName = name.trim()
    setSubmitError(null)

    if (!trimmedName) {
      setNameError('Ingresá el nombre del producto.')
      nameInputRef.current?.focus()
      return
    }

    setNameError(null)
    setIsSubmitting(true)
    try {
      await onSubmit(trimmedName)
    } catch (error) {
      setSubmitError(
        error instanceof Error
          ? error.message
          : 'No pudimos guardar el producto.',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Modal
      closeDisabled={isSubmitting}
      description={
        isEditing
          ? 'Actualizá el nombre que se muestra en cotizaciones e historial.'
          : 'El producto quedará disponible para nuevas cotizaciones.'
      }
      isOpen={isOpen}
      onClose={onClose}
      title={isEditing ? 'Editar producto' : 'Nuevo producto'}
    >
      <form noValidate onSubmit={handleSubmit}>
        <div className="space-y-4 px-5 py-5">
          {submitError ? <InlineFeedback message={submitError} /> : null}
          <div>
            <label className="text-sm font-semibold text-slate-800" htmlFor={`${formId}-name`}>
              Nombre <span aria-hidden="true">*</span>
            </label>
            <input
              aria-describedby={nameError ? `${formId}-name-error` : undefined}
              aria-invalid={Boolean(nameError)}
              autoComplete="off"
              autoFocus
              className="mt-1.5 min-h-11 w-full border border-slate-300 bg-white px-3 py-2 text-base text-slate-950 outline-none transition-colors duration-150 focus:border-amber-500 focus:ring-2 focus:ring-amber-500/30 disabled:bg-slate-100 disabled:text-slate-500 motion-reduce:transition-none"
              data-modal-initial-focus
              disabled={isSubmitting}
              id={`${formId}-name`}
              onChange={(event) => setName(event.target.value)}
              ref={nameInputRef}
              type="text"
              value={name}
            />
            {nameError ? (
              <p className="mt-1.5 text-sm font-medium text-red-700" id={`${formId}-name-error`}>
                {nameError}
              </p>
            ) : null}
          </div>
        </div>

        <footer className="flex flex-wrap justify-end gap-3 border-t border-slate-200 px-5 py-4">
          <button
            className="min-h-11 border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-amber-500 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={isSubmitting}
            onClick={onClose}
            type="button"
          >
            Cancelar
          </button>
          <button
            className="min-h-11 bg-amber-500 px-4 py-2 text-sm font-bold text-slate-950 outline-none transition-colors duration-150 hover:bg-amber-400 focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:ring-offset-2 disabled:cursor-wait disabled:opacity-50 motion-reduce:transition-none"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? 'Guardando…' : isEditing ? 'Guardar cambios' : 'Crear producto'}
          </button>
        </footer>
      </form>
    </Modal>
  )
}
