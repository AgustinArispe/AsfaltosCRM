import { useEffect, useMemo, useState } from 'react'
import { ApiError, isStaleWriteConflict } from '../api/client'
import { deleteCustomer, getCustomer, updateCustomer } from '../api/customers'
import { type ApiSession, listCustomerOpportunities } from '../api/opportunities'
import { useAuth } from '../auth/AuthContext'
import { CustomerFormModal } from '../customers/CustomerFormModal'
import { DeleteCustomerModal } from '../customers/DeleteCustomerModal'
import { customerErrorMessage } from '../customers/errors'
import { LegendaryBadge } from '../customers/LegendaryBadge'
import type { CustomerDetail, CustomerWritePayload } from '../customers/types'
import {
  OPPORTUNITY_STATUS_LABELS,
  OPPORTUNITY_STATUS_TONES,
  SOURCE_LABELS,
} from '../pipeline/config'
import type { OpportunitySummary } from '../pipeline/types'
import { AppLink, navigateToHistoryOrigin } from '../routing/router'
import { Badge } from '../shared/Badge'
import { Button } from '../shared/Button'
import { formatDateTime, formatQuantityKg } from '../shared/formatters'
import { Modal } from '../shared/Modal'
import { LoadingState } from '../shared/StatusStates'

function BackToCustomersLink() {
  return (
    <AppLink
      className='ui-pressable inline-flex min-h-11 items-center gap-2 rounded-[var(--radius-control)] px-2 text-sm font-semibold text-[var(--text-secondary)] outline-none hover:bg-[var(--surface-primary)] hover:text-[var(--text-primary)] focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]'
      onClick={(event) => {
        event.preventDefault()
        navigateToHistoryOrigin({ kind: 'workspace', workspace: 'customers' })
      }}
      to={{ kind: 'workspace', workspace: 'customers' }}
    >
      <svg aria-hidden='true' className='size-4' fill='none' viewBox='0 0 20 20'>
        <path
          d='m12.5 4.5-5.5 5.5 5.5 5.5'
          stroke='currentColor'
          strokeLinecap='round'
          strokeLinejoin='round'
          strokeWidth='1.8'
        />
      </svg>
      Volver a Clientes
    </AppLink>
  )
}

function DetailError({ notFound, onRetry }: { notFound: boolean; onRetry: () => void }) {
  return (
    <section aria-labelledby='customer-detail-error' className='max-w-3xl'>
      <div className='px-5 py-6'>
        <h2 className='text-lg font-semibold text-[var(--text-primary)]' id='customer-detail-error'>
          {notFound ? 'Cliente no encontrado' : 'No pudimos cargar el cliente'}
        </h2>
        <p className='mt-2 text-sm leading-6 text-[var(--text-secondary)]'>
          {notFound
            ? 'El cliente no existe, fue eliminado o ya no está disponible.'
            : 'Revisá tu conexión e intentá nuevamente.'}
        </p>
        {!notFound ? (
          <Button className='mt-4' onClick={onRetry}>
            Reintentar
          </Button>
        ) : null}
      </div>
    </section>
  )
}

function OpportunityProducts({ opportunity }: { opportunity: OpportunitySummary }) {
  if (opportunity.products.length === 0) {
    return <span className='text-[var(--text-tertiary)]'>Sin cotización</span>
  }
  return (
    <ul className='space-y-1'>
      {opportunity.products.map((quotedProduct) => (
        <li key={quotedProduct.product.id}>
          <span className='font-medium text-[var(--text-primary)]'>
            {quotedProduct.product.name}
          </span>
          <span className='text-[var(--text-tertiary)]'>
            {' '}
            · {formatQuantityKg(quotedProduct.quantity_kg)}
          </span>
        </li>
      ))}
    </ul>
  )
}

function CustomerOpportunities({
  customerId,
  opportunities,
}: {
  customerId: number
  opportunities: OpportunitySummary[]
}) {
  if (opportunities.length === 0) {
    return (
      <p className='mt-3 text-sm leading-6 text-[var(--text-secondary)]'>
        Este cliente todavía no tiene oportunidades registradas.
      </p>
    )
  }

  return (
    <section
      aria-label='Oportunidades del cliente. Desplazá horizontalmente para ver todas las columnas.'
      className='mt-4 overflow-x-auto focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]'
    >
      <table className='w-full min-w-[58rem] border-collapse text-left text-sm'>
        <caption className='sr-only'>Historial de oportunidades del cliente</caption>
        <thead>
          <tr className='border-b border-[var(--subtle-border)] text-xs text-[var(--text-secondary)]'>
            <th className='pb-2 pr-4 font-semibold' scope='col'>
              Estado
            </th>
            <th className='px-4 pb-2 font-semibold' scope='col'>
              Origen
            </th>
            <th className='px-4 pb-2 font-semibold' scope='col'>
              Fecha
            </th>
            <th className='px-4 pb-2 font-semibold' scope='col'>
              Productos
            </th>
            <th className='px-4 pb-2 font-semibold' scope='col'>
              Responsable
            </th>
            <th className='pb-2 pl-4 text-right font-semibold' scope='col'>
              Acción
            </th>
          </tr>
        </thead>
        <tbody>
          {opportunities.map((opportunity) => (
            <tr className='border-b border-[var(--divider)] last:border-b-0' key={opportunity.id}>
              <td className='py-3 pr-4'>
                <Badge tone={OPPORTUNITY_STATUS_TONES[opportunity.status]}>
                  {OPPORTUNITY_STATUS_LABELS[opportunity.status]}
                </Badge>
              </td>
              <td className='px-4 py-3 text-[var(--text-secondary)]'>
                {SOURCE_LABELS[opportunity.source]}
              </td>
              <td className='whitespace-nowrap px-4 py-3 text-[var(--text-secondary)]'>
                {formatDateTime(opportunity.created_at)}
              </td>
              <td className='max-w-xs px-4 py-3 text-xs leading-5'>
                <OpportunityProducts opportunity={opportunity} />
              </td>
              <td className='px-4 py-3 text-[var(--text-secondary)]'>
                {opportunity.assigned_user?.full_name ?? 'Sin responsable'}
              </td>
              <td className='py-3 pl-4 text-right'>
                <AppLink
                  aria-label={`Ver detalle de oportunidad ${opportunity.id}`}
                  className='inline-flex min-h-11 items-center px-2 font-semibold text-[var(--text-secondary)] underline decoration-[var(--subtle-border)] underline-offset-4 outline-none hover:text-[var(--text-primary)] focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]'
                  origin={{ kind: 'customer', customerId }}
                  to={{
                    kind: 'opportunity',
                    opportunityId: opportunity.id,
                    surface: opportunity.status === 'PERDIDA' ? 'lost' : 'pipeline',
                  }}
                >
                  Ver detalle
                </AppLink>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

export function CustomerDetailPage({ customerId }: { customerId: number }) {
  const { token, logout, user } = useAuth()
  const [customer, setCustomer] = useState<CustomerDetail | null>(null)
  const [opportunities, setOpportunities] = useState<OpportunitySummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<'not-found' | 'request' | null>(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [isEditing, setIsEditing] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const apiSession = useMemo<ApiSession>(
    () => ({ token: token ?? '', onUnauthorized: logout }),
    [logout, token],
  )

  useEffect(() => {
    void reloadKey
    const controller = new AbortController()
    setCustomer(null)
    setOpportunities([])
    setLoadError(null)
    setIsLoading(true)

    Promise.all([
      getCustomer(customerId, { ...apiSession, signal: controller.signal }),
      listCustomerOpportunities(customerId, {
        ...apiSession,
        signal: controller.signal,
      }),
    ])
      .then(([customerResponse, opportunityResponse]) => {
        setCustomer(customerResponse)
        setOpportunities(opportunityResponse)
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setLoadError(error instanceof ApiError && error.status === 404 ? 'not-found' : 'request')
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false)
      })

    return () => controller.abort()
  }, [apiSession, customerId, reloadKey])

  const close = () => navigateToHistoryOrigin({ kind: 'workspace', workspace: 'customers' })

  return (
    <Modal isOpen onClose={close} size='large' title='Ficha de cliente'>
      <div className='px-4 pt-3'>
        <BackToCustomersLink />
      </div>
      {isLoading ? (
        <LoadingState label='Cargando cliente…' />
      ) : loadError || !customer ? (
        <div className='px-5 pb-5'>
          <DetailError
            notFound={loadError === 'not-found'}
            onRetry={() => setReloadKey((current) => current + 1)}
          />
        </div>
      ) : (
        <article aria-labelledby='customer-name' className='px-5 pb-5 pt-3 sm:px-6'>
          <header className='ui-panel px-5 py-5 sm:px-6'>
            <div className='flex flex-wrap items-start justify-between gap-4'>
              <div>
                <div className='mt-1.5 flex flex-wrap items-center gap-2.5'>
                  <h2
                    className='text-2xl font-semibold tracking-tight text-[var(--text-primary)]'
                    id='customer-name'
                  >
                    {customer.name}
                  </h2>
                  {customer.is_legendary || customer.legendary_historical_override ? (
                    <LegendaryBadge />
                  ) : null}
                </div>
                <p className='mt-1 text-sm text-[var(--text-secondary)]'>
                  {customer.company ?? 'Empresa no informada'}
                </p>
              </div>
              <div className='flex flex-wrap gap-2'>
                <Button onClick={() => setIsEditing(true)}>Editar</Button>
                {user?.role === 'SUPERVISOR' ? (
                  <Button onClick={() => setIsDeleting(true)} variant='danger'>
                    Eliminar
                  </Button>
                ) : null}
              </div>
            </div>
          </header>

          <section
            aria-labelledby='customer-contact-title'
            className='ui-panel mt-4 px-5 py-5 sm:px-6'
          >
            <h3
              className='text-base font-semibold text-[var(--text-primary)]'
              id='customer-contact-title'
            >
              Información de contacto
            </h3>
            <dl className='mt-4 grid gap-x-6 gap-y-4 sm:grid-cols-2 lg:grid-cols-3'>
              <div>
                <dt className='text-xs font-semibold text-[var(--text-tertiary)]'>Email</dt>
                <dd className='mt-1 break-words text-sm text-[var(--text-primary)]'>
                  {customer.email ? (
                    <a
                      className='underline decoration-[var(--subtle-border)] underline-offset-2 outline-none hover:decoration-[var(--strong-border)] focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]'
                      href={`mailto:${customer.email}`}
                    >
                      {customer.email}
                    </a>
                  ) : (
                    'No informado'
                  )}
                </dd>
              </div>
              <div>
                <dt className='text-xs font-semibold text-[var(--text-tertiary)]'>Teléfono</dt>
                <dd className='mt-1 text-sm text-[var(--text-primary)]'>
                  {customer.phone ? (
                    <a
                      className='underline decoration-[var(--subtle-border)] underline-offset-2 outline-none hover:decoration-[var(--strong-border)] focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]'
                      href={`tel:${customer.phone.replace(/[^\d+]/g, '')}`}
                    >
                      {customer.phone}
                    </a>
                  ) : (
                    'No informado'
                  )}
                </dd>
              </div>
              <div>
                <dt className='text-xs font-semibold text-[var(--text-tertiary)]'>Provincia</dt>
                <dd className='mt-1 text-sm text-[var(--text-primary)]'>
                  {customer.province ?? 'No informada'}
                </dd>
              </div>
              <div>
                <dt className='text-xs font-semibold text-[var(--text-tertiary)]'>Fecha de alta</dt>
                <dd className='mt-1 text-sm text-[var(--text-primary)]'>
                  <time dateTime={customer.created_at}>{formatDateTime(customer.created_at)}</time>
                </dd>
              </div>
            </dl>
          </section>

          <section
            aria-labelledby='customer-opportunities-title'
            className='ui-panel mt-4 px-5 py-5 sm:px-6'
          >
            <div className='flex flex-wrap items-baseline justify-between gap-2'>
              <h3
                className='text-base font-semibold text-[var(--text-primary)]'
                id='customer-opportunities-title'
              >
                Oportunidades
              </h3>
              <p className='text-sm text-[var(--text-secondary)]'>
                {opportunities.length}{' '}
                {opportunities.length === 1 ? 'oportunidad' : 'oportunidades'}
              </p>
            </div>
            <CustomerOpportunities customerId={customer.id} opportunities={opportunities} />
          </section>
          <CustomerFormModal
            customer={customer}
            isOpen={isEditing}
            onClose={() => setIsEditing(false)}
            onSubmit={async (payload: CustomerWritePayload) => {
              try {
                const updated = await updateCustomer(
                  customer.id,
                  { ...payload, expected_updated_at: customer.updated_at ?? '' },
                  apiSession,
                )
                setCustomer((current) => (current ? { ...current, ...updated } : current))
                setIsEditing(false)
              } catch (caught) {
                if (isStaleWriteConflict(caught)) {
                  try {
                    const authoritativeCustomer = await getCustomer(customer.id, apiSession)
                    setCustomer(authoritativeCustomer)
                  } catch {
                    // The editor preserves its values even when the authoritative refresh fails.
                  }
                  throw new Error(
                    'Otro cambio fue guardado antes. Actualizamos la versión del cliente; revisá tus cambios y volvé a guardar.',
                  )
                }
                throw new Error(customerErrorMessage(caught, 'save'))
              }
            }}
            role={user?.role ?? 'VENDEDOR'}
          />
          <DeleteCustomerModal
            customer={isDeleting ? customer : null}
            onClose={() => setIsDeleting(false)}
            onConfirm={async () => {
              try {
                await deleteCustomer(customer.id, apiSession)
                navigateToHistoryOrigin({ kind: 'workspace', workspace: 'customers' })
              } catch (caught) {
                throw new Error(customerErrorMessage(caught, 'delete'))
              }
            }}
          />
        </article>
      )}
    </Modal>
  )
}
