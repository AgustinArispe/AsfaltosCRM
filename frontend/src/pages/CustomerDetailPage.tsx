import { useEffect, useMemo, useState } from 'react'

import { getCustomer } from '../api/customers'
import {
  listCustomerOpportunities,
  type ApiSession,
} from '../api/opportunities'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { LegendaryBadge } from '../customers/LegendaryBadge'
import type { CustomerDetail } from '../customers/types'
import {
  OPPORTUNITY_STATUS_BADGE_CLASSES,
  OPPORTUNITY_STATUS_LABELS,
  SOURCE_LABELS,
} from '../pipeline/config'
import type { OpportunitySummary } from '../pipeline/types'
import { AppLink } from '../routing/router'
import { formatDateTime, formatQuantityKg } from '../shared/formatters'
import { LoadingState } from '../shared/LoadingState'

function BackToCustomersLink() {
  return (
    <AppLink
      className="inline-flex min-h-11 items-center gap-2 px-1 text-sm font-semibold text-slate-700 outline-none hover:text-slate-950 focus-visible:ring-2 focus-visible:ring-amber-500"
      to="/customers"
    >
      <svg aria-hidden="true" className="size-4" fill="none" viewBox="0 0 20 20">
        <path d="m12.5 4.5-5.5 5.5 5.5 5.5" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
      </svg>
      Volver a Clientes
    </AppLink>
  )
}

function DetailError({
  notFound,
  onRetry,
}: {
  notFound: boolean
  onRetry: () => void
}) {
  return (
    <section aria-labelledby="customer-detail-error" className="max-w-3xl">
      <BackToCustomersLink />
      <div className="mt-4 border border-slate-200 bg-white px-5 py-6">
        <h2 className="text-lg font-semibold text-slate-950" id="customer-detail-error">
          {notFound ? 'Cliente no encontrado' : 'No pudimos cargar el cliente'}
        </h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          {notFound
            ? 'El cliente no existe, fue eliminado o ya no está disponible.'
            : 'Revisá tu conexión e intentá nuevamente.'}
        </p>
        {!notFound ? (
          <button
            className="mt-4 min-h-11 border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-amber-500"
            onClick={onRetry}
            type="button"
          >
            Reintentar
          </button>
        ) : null}
      </div>
    </section>
  )
}

function OpportunityProducts({ opportunity }: { opportunity: OpportunitySummary }) {
  if (opportunity.products.length === 0) {
    return <span className="text-slate-500">Sin cotización</span>
  }
  return (
    <ul className="space-y-1">
      {opportunity.products.map((quotedProduct) => (
        <li key={quotedProduct.product.id}>
          <span className="font-medium text-slate-800">{quotedProduct.product.name}</span>
          <span className="text-slate-500"> · {formatQuantityKg(quotedProduct.quantity_kg)}</span>
        </li>
      ))}
    </ul>
  )
}

function CustomerOpportunities({ opportunities }: { opportunities: OpportunitySummary[] }) {
  if (opportunities.length === 0) {
    return (
      <p className="mt-3 text-sm leading-6 text-slate-600">
        Este cliente todavía no tiene oportunidades registradas.
      </p>
    )
  }

  return (
    <div
      aria-label="Oportunidades del cliente. Desplazá horizontalmente para ver todas las columnas."
      className="mt-4 overflow-x-auto focus-visible:ring-2 focus-visible:ring-amber-500"
      role="region"
      tabIndex={0}
    >
      <table className="w-full min-w-[58rem] border-collapse text-left text-sm">
        <caption className="sr-only">Historial de oportunidades del cliente</caption>
        <thead>
          <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-600">
            <th className="pb-2 pr-4 font-semibold" scope="col">Estado</th>
            <th className="px-4 pb-2 font-semibold" scope="col">Origen</th>
            <th className="px-4 pb-2 font-semibold" scope="col">Fecha</th>
            <th className="px-4 pb-2 font-semibold" scope="col">Productos</th>
            <th className="px-4 pb-2 font-semibold" scope="col">Responsable</th>
            <th className="pb-2 pl-4 text-right font-semibold" scope="col">Acción</th>
          </tr>
        </thead>
        <tbody>
          {opportunities.map((opportunity) => (
            <tr className="border-b border-slate-100 last:border-b-0" key={opportunity.id}>
              <td className="py-3 pr-4">
                <span className={`inline-flex border px-2.5 py-1 text-xs font-bold ${OPPORTUNITY_STATUS_BADGE_CLASSES[opportunity.status]}`}>
                  {OPPORTUNITY_STATUS_LABELS[opportunity.status]}
                </span>
              </td>
              <td className="px-4 py-3 text-slate-700">{SOURCE_LABELS[opportunity.source]}</td>
              <td className="whitespace-nowrap px-4 py-3 text-slate-700">{formatDateTime(opportunity.created_at)}</td>
              <td className="max-w-xs px-4 py-3 text-xs leading-5"><OpportunityProducts opportunity={opportunity} /></td>
              <td className="px-4 py-3 text-slate-700">{opportunity.assigned_user?.full_name ?? 'Sin responsable'}</td>
              <td className="py-3 pl-4 text-right">
                <AppLink
                  aria-label={`Ver detalle de oportunidad ${opportunity.id}`}
                  className="inline-flex min-h-11 items-center px-2 font-semibold text-slate-700 underline decoration-slate-300 underline-offset-4 outline-none hover:text-slate-950 focus-visible:ring-2 focus-visible:ring-amber-500"
                  to={`/opportunities/${opportunity.id}`}
                >
                  Ver detalle
                </AppLink>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function CustomerDetailPage({ customerId }: { customerId: number }) {
  const { token, logout } = useAuth()
  const [customer, setCustomer] = useState<CustomerDetail | null>(null)
  const [opportunities, setOpportunities] = useState<OpportunitySummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<'not-found' | 'request' | null>(null)
  const [reloadKey, setReloadKey] = useState(0)
  const apiSession = useMemo<ApiSession>(
    () => ({ token: token ?? '', onUnauthorized: logout }),
    [logout, token],
  )

  useEffect(() => {
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
        setLoadError(
          error instanceof ApiError && error.status === 404
            ? 'not-found'
            : 'request',
        )
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false)
      })

    return () => controller.abort()
  }, [apiSession, customerId, reloadKey])

  if (isLoading) return <LoadingState label="Cargando cliente…" />
  if (loadError || !customer) {
    return (
      <DetailError
        notFound={loadError === 'not-found'}
        onRetry={() => setReloadKey((current) => current + 1)}
      />
    )
  }

  return (
    <article aria-labelledby="customer-name" className="mx-auto max-w-6xl">
      <BackToCustomersLink />

      <header className="mt-3 border border-slate-200 bg-white px-5 py-5 sm:px-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Cliente #{customer.id}</p>
            <div className="mt-1.5 flex flex-wrap items-center gap-2.5">
              <h2 className="text-2xl font-semibold tracking-tight text-slate-950" id="customer-name">
                {customer.name}
              </h2>
              {customer.legendary_historical_override ? <LegendaryBadge /> : null}
            </div>
            <p className="mt-1 text-sm text-slate-600">{customer.company ?? 'Empresa no informada'}</p>
          </div>
          <div className="text-left sm:text-right">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Fecha de alta</p>
            <time className="mt-1 block text-sm font-medium text-slate-900" dateTime={customer.created_at}>
              {formatDateTime(customer.created_at)}
            </time>
          </div>
        </div>
      </header>

      <section aria-labelledby="customer-contact-title" className="mt-4 border border-slate-200 bg-white px-5 py-5 sm:px-6">
        <h3 className="text-base font-semibold text-slate-950" id="customer-contact-title">Información de contacto</h3>
        <dl className="mt-4 grid gap-x-6 gap-y-4 sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Email</dt>
            <dd className="mt-1 break-words text-sm text-slate-900">
              {customer.email ? <a className="underline decoration-slate-300 underline-offset-2 outline-none hover:decoration-slate-700 focus-visible:ring-2 focus-visible:ring-amber-500" href={`mailto:${customer.email}`}>{customer.email}</a> : 'No informado'}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Teléfono</dt>
            <dd className="mt-1 text-sm text-slate-900">
              {customer.phone ? <a className="underline decoration-slate-300 underline-offset-2 outline-none hover:decoration-slate-700 focus-visible:ring-2 focus-visible:ring-amber-500" href={`tel:${customer.phone.replace(/[^\d+]/g, '')}`}>{customer.phone}</a> : 'No informado'}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Provincia</dt>
            <dd className="mt-1 text-sm text-slate-900">{customer.province ?? 'No informada'}</dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="customer-opportunities-title" className="mt-4 border border-slate-200 bg-white px-5 py-5 sm:px-6">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h3 className="text-base font-semibold text-slate-950" id="customer-opportunities-title">Oportunidades</h3>
          <p className="text-sm text-slate-600">{opportunities.length} {opportunities.length === 1 ? 'oportunidad' : 'oportunidades'}</p>
        </div>
        <CustomerOpportunities opportunities={opportunities} />
      </section>
    </article>
  )
}
