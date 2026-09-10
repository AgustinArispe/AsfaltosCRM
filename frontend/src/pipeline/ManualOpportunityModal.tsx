import { type FormEvent, useEffect, useId, useState } from 'react'

import { ApiError } from '../api/client'
import { listCustomers } from '../api/customers'
import { type ApiSession, createManualOpportunity } from '../api/opportunities'
import { listUsers } from '../api/users'
import type { AuthUser } from '../auth/types'
import type { CustomerSummary } from '../customers/types'
import { Button } from '../shared/Button'
import { Input, Select } from '../shared/FormControls'
import { Icon } from '../shared/Icon'
import { Modal } from '../shared/Modal'
import { InlineFeedback } from '../shared/StatusStates'
import type { ManualOpportunityCreatePayload, OpportunityDetail } from './types'
import './manual-opportunity.css'

type CustomerMode = 'existing' | 'new'

type NewCustomerValues = {
  name: string
  company: string
  phone: string
  email: string
  province: string
}

const EMPTY_CUSTOMER: NewCustomerValues = {
  name: '',
  company: '',
  phone: '',
  email: '',
  province: '',
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function nullableTrimmed(value: string): string | null {
  return value.trim() || null
}

function customerTitle(customer: CustomerSummary): string {
  return customer.company?.trim() || customer.name
}

function customerSubtitle(customer: CustomerSummary): string {
  return [customer.company ? customer.name : null, customer.email, customer.phone]
    .filter(Boolean)
    .join(' · ')
}

function conflictCode(error: unknown): string | undefined {
  return error instanceof ApiError && typeof error.detail === 'object'
    ? error.detail?.code
    : undefined
}

function submitErrorMessage(error: unknown): string {
  const code = conflictCode(error)
  if (code === 'MANUAL_CUSTOMER_IDENTITY_AMBIGUOUS') {
    return 'El email y el teléfono coinciden con clientes distintos. Revisá los datos antes de continuar.'
  }
  if (code === 'MANUAL_CUSTOMER_IDENTITY_DELETED') {
    return 'Estos datos coinciden con un cliente eliminado. Resolvé ese cliente antes de crear la oportunidad.'
  }
  if (code === 'MANUAL_OPPORTUNITY_COMMAND_CONFLICT') {
    return 'La solicitud cambió durante el reintento. Revisá los datos y volvé a crearla.'
  }
  if (error instanceof ApiError && error.status === 409) {
    return 'Los datos cambiaron antes de guardar. Revisalos e intentá nuevamente.'
  }
  return 'No pudimos crear la oportunidad. Conservamos los datos para que vuelvas a intentar.'
}

export function ManualOpportunityModal({
  isOpen,
  user,
  apiSession,
  returnFocusTo,
  onClose,
  onCreated,
}: {
  isOpen: boolean
  user: AuthUser
  apiSession: ApiSession
  returnFocusTo: HTMLElement | null
  onClose: () => void
  onCreated: (opportunity: OpportunityDetail) => void
}) {
  const [mode, setMode] = useState<CustomerMode>('existing')
  const [search, setSearch] = useState('')
  const [customers, setCustomers] = useState<CustomerSummary[]>([])
  const [selectedCustomer, setSelectedCustomer] = useState<CustomerSummary | null>(null)
  const [isSearching, setIsSearching] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [values, setValues] = useState<NewCustomerValues>(EMPTY_CUSTOMER)
  const [nameError, setNameError] = useState<string | undefined>()
  const [emailError, setEmailError] = useState<string | undefined>()
  const [assigneeId, setAssigneeId] = useState('')
  const [users, setUsers] = useState<AuthUser[]>([])
  const [usersError, setUsersError] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [matchedCustomer, setMatchedCustomer] = useState<CustomerSummary | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [commandId, setCommandId] = useState<string | null>(null)
  const formId = useId()

  useEffect(() => {
    if (!isOpen) return
    setMode('existing')
    setSearch('')
    setCustomers([])
    setSelectedCustomer(null)
    setValues(EMPTY_CUSTOMER)
    setNameError(undefined)
    setEmailError(undefined)
    setAssigneeId('')
    setSubmitError(null)
    setMatchedCustomer(null)
    setCommandId(null)
    setIsSubmitting(false)
  }, [isOpen])

  useEffect(() => {
    if (!isOpen || mode !== 'existing') return
    const normalizedSearch = search.trim()
    if (!normalizedSearch) {
      setCustomers([])
      setSearchError(null)
      setIsSearching(false)
      return
    }
    const controller = new AbortController()
    const timeout = window.setTimeout(() => {
      setIsSearching(true)
      setSearchError(null)
      void listCustomers(
        { page: 1, pageSize: 8, search: normalizedSearch },
        { ...apiSession, signal: controller.signal },
      )
        .then((response) => setCustomers(response.items))
        .catch((error: unknown) => {
          if (error instanceof DOMException && error.name === 'AbortError') return
          setCustomers([])
          setSearchError('No pudimos buscar clientes. Intentá nuevamente.')
        })
        .finally(() => {
          if (!controller.signal.aborted) setIsSearching(false)
        })
    }, 300)
    return () => {
      window.clearTimeout(timeout)
      controller.abort()
    }
  }, [apiSession, isOpen, mode, search])

  useEffect(() => {
    if (!isOpen || user.role !== 'SUPERVISOR') return
    const controller = new AbortController()
    setUsersError(null)
    void listUsers({ ...apiSession, signal: controller.signal })
      .then((items) => setUsers(items.filter((item) => item.is_active)))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setUsersError('No pudimos cargar responsables. Podés crearla sin responsable.')
      })
    return () => controller.abort()
  }, [apiSession, isOpen, user.role])

  const invalidateCommand = () => {
    setCommandId(null)
    setSubmitError(null)
    setMatchedCustomer(null)
  }

  const changeMode = (nextMode: CustomerMode) => {
    setMode(nextMode)
    setSelectedCustomer(null)
    invalidateCommand()
  }

  const updateValue = (key: keyof NewCustomerValues, value: string) => {
    setValues((current) => ({ ...current, [key]: value }))
    if (key === 'name') setNameError(undefined)
    if (key === 'email') setEmailError(undefined)
    invalidateCommand()
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSubmitError(null)
    setMatchedCustomer(null)

    if (mode === 'existing' && !selectedCustomer) {
      setSubmitError('Seleccioná un cliente existente para continuar.')
      return
    }
    if (mode === 'new') {
      const invalidName = !values.name.trim()
      const invalidEmail = Boolean(values.email.trim() && !EMAIL_PATTERN.test(values.email.trim()))
      setNameError(invalidName ? 'Ingresá el nombre del cliente.' : undefined)
      setEmailError(invalidEmail ? 'Ingresá un email válido.' : undefined)
      if (invalidName || invalidEmail) {
        const invalidField = invalidName ? `${formId}-name` : `${formId}-email`
        document.getElementById(invalidField)?.focus()
        return
      }
    }

    const stableCommandId = commandId ?? crypto.randomUUID()
    if (!commandId) setCommandId(stableCommandId)
    const payload: ManualOpportunityCreatePayload = {
      command_id: stableCommandId,
      assigned_user_id: user.role === 'SUPERVISOR' && assigneeId ? Number(assigneeId) : null,
      customer:
        mode === 'existing' && selectedCustomer
          ? { kind: 'existing', customer_id: selectedCustomer.id }
          : {
              kind: 'new',
              name: values.name.trim(),
              company: nullableTrimmed(values.company),
              phone: nullableTrimmed(values.phone),
              email: nullableTrimmed(values.email),
              province: nullableTrimmed(values.province),
            },
    }

    setIsSubmitting(true)
    try {
      const response = await createManualOpportunity(payload, apiSession)
      onCreated(response.opportunity)
    } catch (error) {
      if (
        error instanceof ApiError &&
        conflictCode(error) === 'MANUAL_CUSTOMER_MATCH_EXISTS' &&
        typeof error.detail === 'object' &&
        error.detail.customer
      ) {
        setMatchedCustomer(error.detail.customer)
        setSubmitError('Ya existe un cliente con ese email o teléfono.')
      } else {
        setSubmitError(submitErrorMessage(error))
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const useMatchedCustomer = () => {
    if (!matchedCustomer) return
    setMode('existing')
    setSelectedCustomer(matchedCustomer)
    setSearch(customerTitle(matchedCustomer))
    setCustomers([])
    setMatchedCustomer(null)
    setSubmitError(null)
    setCommandId(null)
  }

  return (
    <Modal
      closeDisabled={isSubmitting}
      description='Registrá un referido con un cliente existente o uno nuevo.'
      isOpen={isOpen}
      onClose={onClose}
      returnFocusTo={returnFocusTo}
      title='Nueva oportunidad'
    >
      <form aria-busy={isSubmitting} noValidate onSubmit={handleSubmit}>
        <div className='manual-opportunity-modal__body'>
          <fieldset className='manual-opportunity-modal__modes'>
            <legend className='sr-only'>Tipo de cliente</legend>
            <button
              aria-pressed={mode === 'existing'}
              className='manual-opportunity-modal__mode'
              disabled={isSubmitting}
              onClick={() => changeMode('existing')}
              type='button'
            >
              Cliente existente
            </button>
            <button
              aria-pressed={mode === 'new'}
              className='manual-opportunity-modal__mode'
              disabled={isSubmitting}
              onClick={() => changeMode('new')}
              type='button'
            >
              Cliente nuevo
            </button>
          </fieldset>

          <div className='manual-opportunity-modal__source'>
            <span className='manual-opportunity-modal__source-icon'>
              <Icon className='manual-opportunity-modal__identity-icon' name='users' />
            </span>
            <span>
              <small>Origen</small>
              <strong>Manual</strong>
            </span>
          </div>

          {submitError ? (
            <div aria-live='assertive'>
              <InlineFeedback message={submitError} />
              {matchedCustomer ? (
                <Button className='mt-3' onClick={useMatchedCustomer} size='compact'>
                  Usar cliente existente
                </Button>
              ) : null}
            </div>
          ) : null}

          {mode === 'existing' ? (
            <div className='manual-opportunity-modal__customer-area'>
              <Input
                autoComplete='off'
                data-modal-initial-focus
                disabled={isSubmitting}
                id={`${formId}-customer-search`}
                label='Buscar cliente'
                onChange={(event) => {
                  setSearch(event.target.value)
                  setSelectedCustomer(null)
                  invalidateCommand()
                }}
                placeholder='Nombre, empresa, email o teléfono'
                type='search'
                value={search}
              />
              {selectedCustomer ? (
                <div className='manual-opportunity-modal__selected'>
                  <span className='manual-opportunity-modal__customer-icon'>
                    <Icon className='manual-opportunity-modal__identity-icon' name='check' />
                  </span>
                  <span>
                    <strong>{customerTitle(selectedCustomer)}</strong>
                    <small>{customerSubtitle(selectedCustomer) || 'Cliente seleccionado'}</small>
                  </span>
                  <Button
                    disabled={isSubmitting}
                    onClick={() => {
                      setSelectedCustomer(null)
                      invalidateCommand()
                    }}
                    size='compact'
                    variant='ghost'
                  >
                    Cambiar
                  </Button>
                </div>
              ) : search.trim() ? (
                <div aria-live='polite' className='manual-opportunity-modal__results'>
                  {isSearching ? <p role='status'>Buscando clientes…</p> : null}
                  {searchError ? <p role='alert'>{searchError}</p> : null}
                  {!isSearching && !searchError && customers.length === 0 ? (
                    <p>No encontramos clientes con esa búsqueda.</p>
                  ) : null}
                  {customers.length > 0 ? (
                    <ul aria-label='Clientes encontrados'>
                      {customers.map((customer) => (
                        <li key={customer.id}>
                          <button
                            className='manual-opportunity-modal__result'
                            disabled={isSubmitting}
                            onClick={() => {
                              setSelectedCustomer(customer)
                              setSearch(customerTitle(customer))
                              setCustomers([])
                              invalidateCommand()
                            }}
                            type='button'
                          >
                            <span>
                              <strong>{customerTitle(customer)}</strong>
                              <small>{customerSubtitle(customer) || 'Sin contacto cargado'}</small>
                            </span>
                            <Icon
                              className='manual-opportunity-modal__result-icon'
                              name='chevron-right'
                            />
                          </button>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ) : (
                <p className='manual-opportunity-modal__hint'>
                  Escribí al menos parte del nombre o contacto para buscar.
                </p>
              )}
            </div>
          ) : (
            <div className='manual-opportunity-modal__new-grid'>
              <Input
                autoComplete='name'
                data-modal-initial-focus
                disabled={isSubmitting}
                error={nameError}
                id={`${formId}-name`}
                label='Nombre *'
                onChange={(event) => updateValue('name', event.target.value)}
                value={values.name}
              />
              <Input
                autoComplete='organization'
                disabled={isSubmitting}
                id={`${formId}-company`}
                label='Empresa'
                onChange={(event) => updateValue('company', event.target.value)}
                value={values.company}
              />
              <Input
                autoComplete='tel'
                disabled={isSubmitting}
                id={`${formId}-phone`}
                inputMode='tel'
                label='Teléfono'
                onChange={(event) => updateValue('phone', event.target.value)}
                type='tel'
                value={values.phone}
              />
              <Input
                autoComplete='email'
                disabled={isSubmitting}
                error={emailError}
                id={`${formId}-email`}
                inputMode='email'
                label='Email'
                onChange={(event) => updateValue('email', event.target.value)}
                type='email'
                value={values.email}
              />
              <div className='sm:col-span-2'>
                <Input
                  autoComplete='address-level1'
                  disabled={isSubmitting}
                  id={`${formId}-province`}
                  label='Provincia'
                  onChange={(event) => updateValue('province', event.target.value)}
                  value={values.province}
                />
              </div>
            </div>
          )}

          <div className='manual-opportunity-modal__responsible'>
            {user.role === 'SUPERVISOR' ? (
              <Select
                description={usersError ?? 'Podés dejar la oportunidad sin responsable.'}
                disabled={isSubmitting}
                id={`${formId}-responsible`}
                label='Responsable'
                onChange={(event) => {
                  setAssigneeId(event.target.value)
                  invalidateCommand()
                }}
                value={assigneeId}
              >
                <option value=''>Sin responsable</option>
                {users.map((responsible) => (
                  <option key={responsible.id} value={responsible.id}>
                    {responsible.full_name}
                  </option>
                ))}
              </Select>
            ) : (
              <div className='manual-opportunity-modal__fixed-responsible'>
                <small>Responsable</small>
                <strong>Sin responsable</strong>
              </div>
            )}
          </div>
        </div>

        <footer className='manual-opportunity-modal__footer'>
          <Button disabled={isSubmitting} onClick={onClose} variant='ghost'>
            Cancelar
          </Button>
          <Button isLoading={isSubmitting} type='submit' variant='primary'>
            <Icon name='check' />
            {isSubmitting ? 'Creando…' : 'Crear oportunidad'}
          </Button>
        </footer>
      </form>
    </Modal>
  )
}
