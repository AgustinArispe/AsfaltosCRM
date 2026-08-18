import type { ReactNode } from 'react'

import { LegendaryBadge } from '../customers/LegendaryBadge'
import { Badge } from '../shared/Badge'
import {
  formatDateTime,
  formatQuantityKg,
  formatStageDuration,
  sumQuantitiesKg,
} from '../shared/formatters'
import {
  LOSS_REASON_LABELS,
  OPPORTUNITY_STATUS_LABELS,
  OPPORTUNITY_STATUS_TONES,
  SOURCE_LABELS,
} from './config'
import type { OpportunityDetail, OpportunityStatusHistory } from './types'

function historyDescription(entry: OpportunityStatusHistory): string {
  if (entry.from_status === null && entry.to_status === 'NUEVA') {
    return 'Consulta creada'
  }

  return `Pasó de ${entry.from_status ? OPPORTUNITY_STATUS_LABELS[entry.from_status] : 'sin estado'} a ${OPPORTUNITY_STATUS_LABELS[entry.to_status]}`
}

function MissingValue({ children }: { children: ReactNode }) {
  return <span className='text-[var(--text-tertiary)]'>{children}</span>
}

export function OpportunityDetailContent({
  opportunity,
  actions,
  contextual,
  layout = 'page',
}: {
  opportunity: OpportunityDetail
  actions?: ReactNode
  contextual?: ReactNode
  layout?: 'drawer' | 'page'
}) {
  const isDrawer = layout === 'drawer'
  const totalQuantityKg = sumQuantitiesKg(
    opportunity.products.map((quotedProduct) => quotedProduct.quantity_kg),
  )

  return (
    <article aria-labelledby={`opportunity-customer-${opportunity.id}`}>
      <header
        className={
          isDrawer ? 'bg-[var(--surface-primary)] px-4 py-4 sm:px-5' : 'ui-panel px-5 py-5 sm:px-6'
        }
      >
        <div className='flex flex-wrap items-start justify-between gap-3'>
          <div className='min-w-0'>
            <p className='text-xs font-semibold text-[var(--text-tertiary)]'>
              Oportunidad #{opportunity.id}
            </p>
            <div className='mt-1.5 flex flex-wrap items-center gap-2'>
              <h2
                className={`${isDrawer ? 'text-xl' : 'text-2xl'} font-semibold tracking-tight text-[var(--text-primary)]`}
                id={`opportunity-customer-${opportunity.id}`}
              >
                {opportunity.customer.company ?? opportunity.customer.name}
              </h2>
              {opportunity.customer.legendary_historical_override ? <LegendaryBadge /> : null}
            </div>
            {opportunity.customer.company ? (
              <p className='mt-1 text-sm text-[var(--text-secondary)]'>
                Contacto: {opportunity.customer.name}
              </p>
            ) : null}
          </div>
          <Badge tone={OPPORTUNITY_STATUS_TONES[opportunity.status]}>
            {OPPORTUNITY_STATUS_LABELS[opportunity.status]}
          </Badge>
        </div>

        <dl className='mt-4 grid gap-x-5 gap-y-3 border-t border-[var(--subtle-border)] pt-4 sm:grid-cols-2'>
          <div>
            <dt className='text-xs font-medium text-[var(--text-tertiary)]'>Origen</dt>
            <dd className='mt-0.5 text-sm font-medium text-[var(--text-primary)]'>
              {SOURCE_LABELS[opportunity.source]}
            </dd>
          </div>
          <div>
            <dt className='text-xs font-medium text-[var(--text-tertiary)]'>Responsable</dt>
            <dd className='mt-0.5 text-sm font-medium text-[var(--text-primary)]'>
              {opportunity.assigned_user?.full_name ?? 'Sin responsable'}
            </dd>
          </div>
          <div>
            <dt className='text-xs font-medium text-[var(--text-tertiary)]'>Creada</dt>
            <dd className='mt-0.5 text-sm text-[var(--text-primary)]'>
              {formatDateTime(opportunity.created_at)}
            </dd>
          </div>
          <div>
            <dt className='text-xs font-medium text-[var(--text-tertiary)]'>Tiempo en etapa</dt>
            <dd className='mt-0.5 text-sm text-[var(--text-primary)]'>
              {formatStageDuration(opportunity.current_status_entered_at)}
            </dd>
          </div>
        </dl>

        {opportunity.status === 'PERDIDA' && opportunity.loss_reason ? (
          <div className='mt-4 rounded-[var(--radius-control)] border border-[var(--destructive-border)] bg-[var(--destructive-subtle)] px-3 py-2.5'>
            <p className='text-xs font-medium text-[var(--destructive-text)]'>Motivo de pérdida</p>
            <p className='mt-0.5 text-sm font-semibold text-[var(--destructive-text)]'>
              {LOSS_REASON_LABELS[opportunity.loss_reason]}
            </p>
          </div>
        ) : null}

        {actions ? (
          <div className='mt-4 flex flex-wrap gap-2 border-t border-[var(--subtle-border)] pt-4'>
            {actions}
          </div>
        ) : null}
      </header>

      <div
        className={
          isDrawer
            ? 'space-y-3 border-t border-[var(--subtle-border)] bg-[var(--surface-secondary)] p-3 sm:p-4'
            : 'mt-4 grid items-start gap-4 lg:grid-cols-[minmax(0,1.35fr)_minmax(19rem,0.8fr)]'
        }
      >
        <div className='space-y-3'>
          <section
            aria-labelledby={`customer-information-${opportunity.id}`}
            className='ui-panel px-4 py-4 sm:px-5'
          >
            <h3
              className='text-sm font-semibold text-[var(--text-primary)]'
              id={`customer-information-${opportunity.id}`}
            >
              Información del cliente
            </h3>
            <dl className='mt-3 grid gap-x-5 gap-y-3 sm:grid-cols-2'>
              <div>
                <dt className='text-xs font-medium text-[var(--text-tertiary)]'>Email</dt>
                <dd className='mt-0.5 break-words text-sm text-[var(--text-primary)]'>
                  {opportunity.customer.email ? (
                    <a
                      className='underline decoration-[var(--subtle-border)] underline-offset-2 hover:decoration-[var(--strong-border)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]'
                      href={`mailto:${opportunity.customer.email}`}
                    >
                      {opportunity.customer.email}
                    </a>
                  ) : (
                    <MissingValue>No informado</MissingValue>
                  )}
                </dd>
              </div>
              <div>
                <dt className='text-xs font-medium text-[var(--text-tertiary)]'>Teléfono</dt>
                <dd className='mt-0.5 text-sm text-[var(--text-primary)]'>
                  {opportunity.customer.phone ? (
                    <a
                      className='underline decoration-[var(--subtle-border)] underline-offset-2 hover:decoration-[var(--strong-border)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]'
                      href={`tel:${opportunity.customer.phone}`}
                    >
                      {opportunity.customer.phone}
                    </a>
                  ) : (
                    <MissingValue>No informado</MissingValue>
                  )}
                </dd>
              </div>
              <div>
                <dt className='text-xs font-medium text-[var(--text-tertiary)]'>Provincia</dt>
                <dd className='mt-0.5 text-sm text-[var(--text-primary)]'>
                  {opportunity.customer.province ?? <MissingValue>No informada</MissingValue>}
                </dd>
              </div>
            </dl>
          </section>

          <section
            aria-labelledby={`quote-${opportunity.id}`}
            className='ui-panel px-4 py-4 sm:px-5'
          >
            <h3
              className='text-sm font-semibold text-[var(--text-primary)]'
              id={`quote-${opportunity.id}`}
            >
              Cotización
            </h3>
            {opportunity.products.length > 0 ? (
              <div className='mt-3 overflow-x-auto'>
                <table
                  aria-label='Productos y cantidades cotizadas'
                  className='w-full border-collapse text-left text-sm'
                >
                  <thead>
                    <tr className='border-b border-[var(--subtle-border)] text-xs text-[var(--text-tertiary)]'>
                      <th className='pb-2 font-medium' scope='col'>
                        Producto
                      </th>
                      <th className='pb-2 text-right font-medium' scope='col'>
                        Cantidad
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {opportunity.products.map((quotedProduct) => (
                      <tr
                        className='border-b border-[var(--divider)] last:border-b-0'
                        key={quotedProduct.product.id}
                      >
                        <th className='py-2.5 font-medium text-[var(--text-primary)]' scope='row'>
                          {quotedProduct.product.name}
                          {!quotedProduct.product.is_active ? (
                            <span className='ml-2 text-xs font-normal text-[var(--text-tertiary)]'>
                              Inactivo
                            </span>
                          ) : null}
                        </th>
                        <td className='py-2.5 text-right tabular-nums text-[var(--text-secondary)]'>
                          {formatQuantityKg(quotedProduct.quantity_kg)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className='border-t border-[var(--subtle-border)]'>
                      <th className='pt-3 font-semibold text-[var(--text-primary)]' scope='row'>
                        Total cotizado
                      </th>
                      <td className='pt-3 text-right font-semibold tabular-nums text-[var(--text-primary)]'>
                        {formatQuantityKg(totalQuantityKg)}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            ) : (
              <p className='mt-2 text-sm text-[var(--text-secondary)]'>
                Aún no se registró una cotización.
              </p>
            )}
          </section>
        </div>

        {contextual ?? (
          <section
            aria-labelledby={`history-${opportunity.id}`}
            className='ui-panel px-4 py-4 sm:px-5'
          >
            <h3
              className='text-sm font-semibold text-[var(--text-primary)]'
              id={`history-${opportunity.id}`}
            >
              Historial
            </h3>
            <ol className='mt-3'>
              {opportunity.history.map((entry, index) => (
                <li
                  className='relative grid grid-cols-[0.75rem_minmax(0,1fr)] gap-3 pb-4 last:pb-0'
                  key={entry.id}
                >
                  <div aria-hidden='true' className='relative flex justify-center'>
                    <span className='mt-1.5 size-2 rounded-full bg-[var(--text-tertiary)] ring-2 ring-[var(--surface-primary)]' />
                    {index < opportunity.history.length - 1 ? (
                      <span className='absolute bottom-0 top-4 w-px bg-[var(--divider)]' />
                    ) : null}
                  </div>
                  <div>
                    <time
                      className='text-xs text-[var(--text-tertiary)]'
                      dateTime={entry.changed_at}
                    >
                      {formatDateTime(entry.changed_at)}
                    </time>
                    <p className='mt-0.5 text-sm font-medium leading-5 text-[var(--text-primary)]'>
                      {historyDescription(entry)}
                    </p>
                    {entry.from_status === null ? (
                      <p className='mt-0.5 text-xs text-[var(--text-tertiary)]'>
                        Estado inicial: {OPPORTUNITY_STATUS_LABELS[entry.to_status]}
                      </p>
                    ) : null}
                  </div>
                </li>
              ))}
            </ol>
          </section>
        )}
      </div>
    </article>
  )
}
