import { type FormEvent, useEffect, useId, useRef, useState } from 'react'
import { Button } from '../shared/Button'
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
      setSubmitError(error instanceof Error ? error.message : 'No pudimos guardar el producto.')
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
        <div className='space-y-4 px-5 py-5'>
          {submitError ? <InlineFeedback message={submitError} /> : null}
          <div>
            <label className='ui-label' htmlFor={`${formId}-name`}>
              Nombre <span aria-hidden='true'>*</span>
            </label>
            <input
              aria-describedby={nameError ? `${formId}-name-error` : undefined}
              aria-invalid={Boolean(nameError)}
              autoComplete='off'
              className='ui-field text-base'
              data-modal-initial-focus
              disabled={isSubmitting}
              id={`${formId}-name`}
              onChange={(event) => setName(event.target.value)}
              ref={nameInputRef}
              type='text'
              value={name}
            />
            {nameError ? (
              <p className='mt-1.5 text-sm font-medium text-red-700' id={`${formId}-name-error`}>
                {nameError}
              </p>
            ) : null}
          </div>
        </div>

        <footer className='flex flex-wrap justify-end gap-3 border-t border-slate-200 px-5 py-4'>
          <Button disabled={isSubmitting} onClick={onClose}>
            Cancelar
          </Button>
          <Button disabled={isSubmitting} type='submit' variant='primary'>
            {isSubmitting ? 'Guardando…' : isEditing ? 'Guardar cambios' : 'Crear producto'}
          </Button>
        </footer>
      </form>
    </Modal>
  )
}
