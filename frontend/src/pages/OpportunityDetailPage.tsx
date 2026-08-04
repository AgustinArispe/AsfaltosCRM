import { useEffect, useMemo, useState } from 'react'

import {
  getOpportunityDetail,
  type ApiSession,
} from '../api/opportunities'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import {
  LOSS_REASON_LABELS,
  OPPORTUNITY_STATUS_BADGE_CLASSES,
  OPPORTUNITY_STATUS_LABELS,
  SOURCE_LABELS,
} from '../pipeline/config'
import type {
  OpportunityDetail,
  OpportunityStatusHistory,
} from '../pipeline/types'
import { AppLink } from '../routing/router'
import {
  formatDateTime,
  formatQuantityKg,
  formatStageDuration,
  sumQuantitiesKg,
} from '../shared/formatters'
import { LoadingState } from '../shared/LoadingState'

function BackToPipelineLink() {
  return (
    <AppLink
      className="inline-flex min-h-11 items-center gap-2 px-1 text-sm font-semibold text-slate-700 outline-none hover:text-slate-950 focus-visible:ring-2 focus-visible:ring-amber-500"
      to="/pipeline"
    >
      <svg aria-hidden="true" className="size-4" fill="none" viewBox="0 0 20 20">
        <path d="m12.5 4.5-5.5 5.5 5.5 5.5" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
      </svg>
      Volver al Pipeline
    </AppLink>
  )
}

function StatusBadge({ status }: { status: OpportunityDetail['status'] }) {
  return (
    <span
      className={`inline-flex border px-2.5 py-1 text-xs font-bold ${OPPORTUNITY_STATUS_BADGE_CLASSES[status]}`}
    >
      {OPPORTUNITY_STATUS_LABELS[status]}
    </span>
  )
}

function historyDescription(entry: OpportunityStatusHistory): string {
  if (entry.from_status === null && entry.to_status === 'NUEVA') {
    return 'Consulta creada'
  }

  return `Pasó de ${entry.from_status ? OPPORTUNITY_STATUS_LABELS[entry.from_status] : 'sin estado'} a ${OPPORTUNITY_STATUS_LABELS[entry.to_status]}`
}

function DetailError({
  notFound,
  onRetry,
}: {
  notFound: boolean
  onRetry: () => void
}) {
  return (
    <section aria-labelledby="opportunity-error-title" className="max-w-3xl">
      <BackToPipelineLink />
      <div className="mt-4 border border-slate-200 bg-white px-5 py-6">
        <h2 className="text-lg font-semibold text-slate-950" id="opportunity-error-title">
          {notFound ? 'Oportunidad no encontrada' : 'No pudimos cargar la oportunidad'}
        </h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          {notFound
            ? 'La oportunidad no existe, fue eliminada o ya no está disponible.'
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

export function OpportunityDetailPage({
  opportunityId,
}: {
  opportunityId: number
}) {
  const { token, logout } = useAuth()
  const [opportunity, setOpportunity] = useState<OpportunityDetail | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<'not-found' | 'request' | null>(null)
  const [reloadKey, setReloadKey] = useState(0)

  const apiSession = useMemo<ApiSession>(
    () => ({ token: token ?? '', onUnauthorized: logout }),
    [logout, token],
  )

  useEffect(() => {
    const controller = new AbortController()
    setOpportunity(null)
    setLoadError(null)
    setIsLoading(true)

    getOpportunityDetail(opportunityId, {
      ...apiSession,
      signal: controller.signal,
    })
      .then(setOpportunity)
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
  }, [apiSession, opportunityId, reloadKey])

  if (isLoading) {
    return <LoadingState label="Cargando oportunidad…" />
  }

  if (loadError || !opportunity) {
    return (
      <DetailError
        notFound={loadError === 'not-found'}
        onRetry={() => setReloadKey((current) => current + 1)}
      />
    )
  }

  const totalQuantityKg = sumQuantitiesKg(
    opportunity.products.map((quotedProduct) => quotedProduct.quantity_kg),
  )

  return (
    <article aria-labelledby="opportunity-customer-name" className="mx-auto max-w-6xl">
      <BackToPipelineLink />

      <header className="mt-3 border border-slate-200 bg-white px-5 py-5 sm:px-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
              Oportunidad #{opportunity.id}
            </p>
            <div className="mt-1.5 flex flex-wrap items-center gap-2.5">
              <h2 className="text-2xl font-semibold tracking-tight text-slate-950" id="opportunity-customer-name">
                {opportunity.customer.name}
              </h2>
              {opportunity.customer.legendary_historical_override ? (
                <span className="inline-flex items-center gap-1.5 border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-bold text-amber-900">
                  <svg aria-hidden="true" className="size-3.5 fill-amber-500" viewBox="0 0 20 20">
                    <path d="m10 1.8 2.45 4.97 5.49.8-3.97 3.86.94 5.47L10 14.32 5.09 16.9l.94-5.47-3.97-3.86 5.49-.8L10 1.8Z" />
                  </svg>
                  Legendario
                </span>
              ) : null}
            </div>
            <p className="mt-1 text-sm text-slate-600">
              {opportunity.customer.company ?? 'Empresa no informada'}
            </p>
          </div>
          <StatusBadge status={opportunity.status} />
        </div>

        <dl className="mt-5 grid gap-x-6 gap-y-4 border-t border-slate-200 pt-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Origen</dt>
            <dd className="mt-1 text-sm font-medium text-slate-900">{SOURCE_LABELS[opportunity.source]}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Responsable</dt>
            <dd className="mt-1 text-sm font-medium text-slate-900">
              {opportunity.assigned_user?.full_name ?? 'Sin responsable'}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Creada</dt>
            <dd className="mt-1 text-sm font-medium text-slate-900">{formatDateTime(opportunity.created_at)}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Tiempo en etapa</dt>
            <dd className="mt-1 text-sm font-medium text-slate-900">{formatStageDuration(opportunity.current_status_entered_at)}</dd>
          </div>
        </dl>

        {opportunity.status === 'PERDIDA' && opportunity.loss_reason ? (
          <div className="mt-4 border-l-2 border-red-500 bg-red-50 px-3.5 py-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-red-700">Motivo de pérdida</p>
            <p className="mt-1 text-sm font-semibold text-red-900">{LOSS_REASON_LABELS[opportunity.loss_reason]}</p>
          </div>
        ) : null}
      </header>

      <div className="mt-4 grid items-start gap-4 lg:grid-cols-[minmax(0,1.45fr)_minmax(19rem,0.8fr)]">
        <div className="space-y-4">
          <section aria-labelledby="customer-information-title" className="border border-slate-200 bg-white px-5 py-5 sm:px-6">
            <h3 className="text-base font-semibold text-slate-950" id="customer-information-title">
              Información del cliente
            </h3>
            <dl className="mt-4 grid gap-x-6 gap-y-4 sm:grid-cols-2">
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Email</dt>
                <dd className="mt-1 break-words text-sm text-slate-900">{opportunity.customer.email ?? 'No informado'}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Teléfono</dt>
                <dd className="mt-1 text-sm text-slate-900">{opportunity.customer.phone ?? 'No informado'}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Provincia</dt>
                <dd className="mt-1 text-sm text-slate-900">{opportunity.customer.province ?? 'No informada'}</dd>
              </div>
            </dl>
          </section>

          <section aria-labelledby="quote-title" className="border border-slate-200 bg-white px-5 py-5 sm:px-6">
            <h3 className="text-base font-semibold text-slate-950" id="quote-title">
              Cotización
            </h3>
            {opportunity.products.length > 0 ? (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full border-collapse text-left text-sm">
                  <caption className="sr-only">Productos y cantidades cotizadas</caption>
                  <thead>
                    <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                      <th className="pb-2 font-semibold" scope="col">Producto</th>
                      <th className="pb-2 text-right font-semibold" scope="col">Cantidad</th>
                    </tr>
                  </thead>
                  <tbody>
                    {opportunity.products.map((quotedProduct) => (
                      <tr className="border-b border-slate-100" key={quotedProduct.product.id}>
                        <th className="py-3 font-medium text-slate-900" scope="row">{quotedProduct.product.name}</th>
                        <td className="py-3 text-right tabular-nums text-slate-700">{formatQuantityKg(quotedProduct.quantity_kg)}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr>
                      <th className="pt-3 font-semibold text-slate-950" scope="row">Total cotizado</th>
                      <td className="pt-3 text-right font-bold tabular-nums text-slate-950">{formatQuantityKg(totalQuantityKg)}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            ) : (
              <p className="mt-3 text-sm leading-6 text-slate-600">
                Aún no se registró una cotización.
              </p>
            )}
          </section>
        </div>

        <section aria-labelledby="history-title" className="border border-slate-200 bg-white px-5 py-5 sm:px-6">
          <h3 className="text-base font-semibold text-slate-950" id="history-title">
            Historial
          </h3>
          <ol className="mt-4 space-y-0">
            {opportunity.history.map((entry, index) => (
              <li className="relative grid grid-cols-[0.75rem_minmax(0,1fr)] gap-3 pb-5 last:pb-0" key={entry.id}>
                <div aria-hidden="true" className="relative flex justify-center">
                  <span className="mt-1.5 size-2.5 border-2 border-white bg-slate-500 ring-1 ring-slate-400" />
                  {index < opportunity.history.length - 1 ? (
                    <span className="absolute bottom-0 top-4 w-px bg-slate-200" />
                  ) : null}
                </div>
                <div>
                  <time className="text-xs font-medium text-slate-500" dateTime={entry.changed_at}>
                    {formatDateTime(entry.changed_at)}
                  </time>
                  <p className="mt-1 text-sm font-semibold leading-5 text-slate-900">
                    {historyDescription(entry)}
                  </p>
                  {entry.from_status === null ? (
                    <p className="mt-0.5 text-xs text-slate-600">
                      Estado inicial: {OPPORTUNITY_STATUS_LABELS[entry.to_status]}
                    </p>
                  ) : null}
                </div>
              </li>
            ))}
          </ol>
        </section>
      </div>
    </article>
  )
}
