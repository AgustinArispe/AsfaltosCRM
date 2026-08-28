import { type FormEvent, useEffect, useId, useRef, useState } from 'react'

import type { UserRole } from '../auth/types'
import { Button } from '../shared/Button'
import { Modal } from '../shared/Modal'
import { InlineFeedback } from '../shared/StatusStates'
import type { CustomerFormValues, CustomerSummary, CustomerWritePayload } from './types'

const EMPTY_VALUES: CustomerFormValues = {
  name: '',
  company: '',
  email: '',
  phone: '',
  province: '',
  legendary_historical_override: false,
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function valuesFromCustomer(customer: CustomerSummary | null): CustomerFormValues {
  if (!customer) return EMPTY_VALUES
  return {
    name: customer.name,
    company: customer.company ?? '',
    email: customer.email ?? '',
    phone: customer.phone ?? '',
    province: customer.province ?? '',
    legendary_historical_override: customer.legendary_historical_override,
  }
}

function nullableTrimmed(value: string): string | null {
  const trimmed = value.trim()
  return trimmed || null
}

export function CustomerFormModal({
  isOpen,
  customer,
  role,
  onClose,
  onSubmit,
}: {
  isOpen: boolean
  customer: CustomerSummary | null
  role: UserRole
  onClose: () => void
  onSubmit: (payload: CustomerWritePayload) => Promise<void>
}) {
  const [values, setValues] = useState<CustomerFormValues>(EMPTY_VALUES)
  const [fieldErrors, setFieldErrors] = useState<{
    name?: string
    email?: string
  }>({})
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isDirty, setIsDirty] = useState(false)
  const formId = useId()
  const nameInputRef = useRef<HTMLInputElement>(null)
  const emailInputRef = useRef<HTMLInputElement>(null)
  const isEditing = customer !== null
  const customerRef = useRef(customer)
  customerRef.current = customer

  useEffect(() => {
    if (!isOpen) return
    setValues(valuesFromCustomer(customerRef.current))
    setFieldErrors({})
    setSubmitError(null)
    setIsSubmitting(false)
    setIsDirty(false)
  }, [isOpen])

  const updateValue = <Key extends keyof CustomerFormValues>(
    key: Key,
    value: CustomerFormValues[Key],
  ) => {
    setIsDirty(true)
    setValues((current) => ({ ...current, [key]: value }))
  }

  const requestClose = () => {
    if (isDirty) {
      setSubmitError(
        'Tenés cambios sin guardar. Elegí “Descartar cambios” para salir sin guardarlos.',
      )
      return
    }
    onClose()
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const nextErrors: { name?: string; email?: string } = {}
    if (!values.name.trim()) nextErrors.name = 'Ingresá el nombre del cliente.'
    if (values.email.trim() && !EMAIL_PATTERN.test(values.email.trim())) {
      nextErrors.email = 'Ingresá un email válido.'
    }
    setFieldErrors(nextErrors)
    setSubmitError(null)

    if (Object.keys(nextErrors).length > 0) {
      if (nextErrors.name) nameInputRef.current?.focus()
      else emailInputRef.current?.focus()
      return
    }

    const payload: CustomerWritePayload = {
      name: values.name.trim(),
      company: nullableTrimmed(values.company),
      email: nullableTrimmed(values.email),
      phone: nullableTrimmed(values.phone),
      province: nullableTrimmed(values.province),
    }
    if (role === 'SUPERVISOR') {
      payload.legendary_historical_override = values.legendary_historical_override
    }

    setIsSubmitting(true)
    try {
      await onSubmit(payload)
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'No pudimos guardar el cliente.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const inputClasses = 'ui-field text-base'

  return (
    <Modal
      closeDisabled={isSubmitting}
      description={
        isEditing
          ? 'Actualizá los datos comerciales del cliente.'
          : 'Registrá la información disponible. Solo el nombre es obligatorio.'
      }
      isOpen={isOpen}
      onClose={requestClose}
      title={isEditing ? 'Editar cliente' : 'Nuevo cliente'}
    >
      <form id={formId} noValidate onSubmit={handleSubmit}>
        <div className='max-h-[65dvh] space-y-4 overflow-y-auto px-5 py-5'>
          {submitError ? <InlineFeedback message={submitError} /> : null}

          <div>
            <label className='ui-label' htmlFor={`${formId}-name`}>
              Nombre <span aria-hidden='true'>*</span>
            </label>
            <input
              aria-describedby={fieldErrors.name ? `${formId}-name-error` : undefined}
              aria-invalid={Boolean(fieldErrors.name)}
              autoComplete='name'
              className={inputClasses}
              data-modal-initial-focus
              disabled={isSubmitting}
              id={`${formId}-name`}
              onChange={(event) => updateValue('name', event.target.value)}
              ref={nameInputRef}
              type='text'
              value={values.name}
            />
            {fieldErrors.name ? (
              <p
                className='mt-1.5 text-sm font-medium text-[var(--destructive-text)]'
                id={`${formId}-name-error`}
              >
                {fieldErrors.name}
              </p>
            ) : null}
          </div>

          <div className='grid gap-4 sm:grid-cols-2'>
            <div className='sm:col-span-2'>
              <label className='ui-label' htmlFor={`${formId}-company`}>
                Empresa
              </label>
              <input
                autoComplete='organization'
                className={inputClasses}
                disabled={isSubmitting}
                id={`${formId}-company`}
                onChange={(event) => updateValue('company', event.target.value)}
                type='text'
                value={values.company}
              />
            </div>
            <div>
              <label className='ui-label' htmlFor={`${formId}-email`}>
                Email
              </label>
              <input
                aria-describedby={fieldErrors.email ? `${formId}-email-error` : undefined}
                aria-invalid={Boolean(fieldErrors.email)}
                autoComplete='email'
                className={inputClasses}
                disabled={isSubmitting}
                id={`${formId}-email`}
                inputMode='email'
                onChange={(event) => updateValue('email', event.target.value)}
                ref={emailInputRef}
                type='email'
                value={values.email}
              />
              {fieldErrors.email ? (
                <p
                  className='mt-1.5 text-sm font-medium text-[var(--destructive-text)]'
                  id={`${formId}-email-error`}
                >
                  {fieldErrors.email}
                </p>
              ) : null}
            </div>
            <div>
              <label className='ui-label' htmlFor={`${formId}-phone`}>
                Teléfono
              </label>
              <input
                autoComplete='tel'
                className={inputClasses}
                disabled={isSubmitting}
                id={`${formId}-phone`}
                inputMode='tel'
                onChange={(event) => updateValue('phone', event.target.value)}
                type='tel'
                value={values.phone}
              />
            </div>
            <div className='sm:col-span-2'>
              <label className='ui-label' htmlFor={`${formId}-province`}>
                Provincia
              </label>
              <input
                autoComplete='address-level1'
                className={inputClasses}
                disabled={isSubmitting}
                id={`${formId}-province`}
                onChange={(event) => updateValue('province', event.target.value)}
                type='text'
                value={values.province}
              />
            </div>
          </div>

          {role === 'SUPERVISOR' ? (
            <label className='flex min-h-11 items-start gap-3 rounded-[var(--radius-control)] border border-[var(--subtle-border)] bg-[var(--surface-interactive)] px-3.5 py-3 text-sm text-[var(--text-primary)]'>
              <input
                checked={values.legendary_historical_override}
                className='mt-0.5 size-4 accent-[var(--accent)] focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)] focus-visible:ring-offset-2'
                disabled={isSubmitting}
                onChange={(event) =>
                  updateValue('legendary_historical_override', event.target.checked)
                }
                type='checkbox'
              />
              <span>
                <span className='font-semibold'>Legendario histórico</span>
                <span className='mt-0.5 block text-xs leading-5 text-[var(--text-secondary)]'>
                  FAA reconoció esta relación comercial como histórica antes del CRM.
                </span>
              </span>
            </label>
          ) : null}
        </div>

        <footer className='flex flex-wrap justify-end gap-3 border-t border-[var(--subtle-border)] px-5 py-4'>
          <Button disabled={isSubmitting} onClick={isDirty ? onClose : requestClose}>
            {isDirty ? 'Descartar cambios' : 'Cancelar'}
          </Button>
          <Button disabled={isSubmitting} type='submit' variant='primary'>
            {isSubmitting ? 'Guardando…' : isEditing ? 'Guardar cambios' : 'Crear cliente'}
          </Button>
        </footer>
      </form>
    </Modal>
  )
}
