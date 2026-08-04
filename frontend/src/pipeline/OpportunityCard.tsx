import { useDraggable } from '@dnd-kit/react'

import { AppLink } from '../routing/router'
import { formatQuantityKg, formatTimeInStage } from '../shared/formatters'
import { SOURCE_LABELS, STAGE_BY_STATUS } from './config'
import type { OpportunitySummary, PipelineStatus } from './types'

export type PipelineDragData = {
  opportunityId: number
  customerName: string
  fromStatus: PipelineStatus
  toStatus: PipelineStatus
}

export function OpportunityCard({
  opportunity,
  isBusy,
  onMove,
  onLose,
}: {
  opportunity: OpportunitySummary & { status: PipelineStatus }
  isBusy: boolean
  onMove: (opportunityId: number, targetStatus: PipelineStatus) => void
  onLose: (opportunityId: number) => void
}) {
  const stage = STAGE_BY_STATUS.get(opportunity.status)
  const nextStatus = stage?.nextStatus ?? null
  const nextStage = nextStatus ? STAGE_BY_STATUS.get(nextStatus) : null
  const isDraggable = Boolean(nextStatus) && !isBusy
  const { ref, handleRef, isDragging } = useDraggable<PipelineDragData>({
    id: opportunity.id,
    type: nextStatus ?? 'CLOSED',
    disabled: !isDraggable,
    data: nextStatus
      ? {
          opportunityId: opportunity.id,
          customerName: opportunity.customer.name,
          fromStatus: opportunity.status,
          toStatus: nextStatus,
        }
      : undefined,
  })

  return (
    <article
      aria-busy={isBusy}
      className={[
        'border border-slate-200 bg-white px-3 py-3 shadow-[0_1px_2px_rgb(15_23_42_/_0.06)]',
        isDragging ? 'opacity-45 shadow-lg' : '',
      ].join(' ')}
      data-opportunity-id={opportunity.id}
      ref={ref}
    >
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold leading-5 text-slate-950">
            {opportunity.customer.name}
          </h3>
          {opportunity.customer.company ? (
            <p className="mt-0.5 truncate text-xs text-slate-600" title={opportunity.customer.company}>
              {opportunity.customer.company}
            </p>
          ) : null}
        </div>

        {nextStatus ? (
          <button
            aria-label={`Arrastrar oportunidad de ${opportunity.customer.name} hacia ${nextStage?.label}`}
            className="grid size-11 shrink-0 cursor-grab touch-none place-items-center text-slate-400 outline-none transition-colors duration-150 hover:bg-slate-100 hover:text-slate-700 focus-visible:ring-2 focus-visible:ring-amber-500 active:cursor-grabbing disabled:cursor-not-allowed disabled:opacity-40 motion-reduce:transition-none"
            disabled={isBusy}
            ref={handleRef}
            type="button"
          >
            <svg aria-hidden="true" className="size-5" fill="currentColor" viewBox="0 0 20 20">
              <circle cx="7" cy="5" r="1.25" />
              <circle cx="13" cy="5" r="1.25" />
              <circle cx="7" cy="10" r="1.25" />
              <circle cx="13" cy="10" r="1.25" />
              <circle cx="7" cy="15" r="1.25" />
              <circle cx="13" cy="15" r="1.25" />
            </svg>
          </button>
        ) : null}
      </div>

      {opportunity.products.length > 0 ? (
        <ul className="mt-2.5 space-y-1 border-t border-slate-100 pt-2.5">
          {opportunity.products.slice(0, 2).map((quotedProduct) => (
            <li className="flex items-baseline justify-between gap-2 text-xs" key={quotedProduct.product.id}>
              <span className="min-w-0 truncate font-medium text-slate-700">
                {quotedProduct.product.name}
              </span>
              <span className="shrink-0 tabular-nums text-slate-500">
                {formatQuantityKg(quotedProduct.quantity_kg)}
              </span>
            </li>
          ))}
          {opportunity.products.length > 2 ? (
            <li className="text-xs font-medium text-slate-500">
              +{opportunity.products.length - 2} productos
            </li>
          ) : null}
        </ul>
      ) : null}

      <div className="mt-2.5 border-t border-slate-100 pt-2.5 text-xs leading-5 text-slate-500">
        <p>
          {SOURCE_LABELS[opportunity.source]} ·{' '}
          <span>{formatTimeInStage(opportunity.current_status_entered_at)}</span>
        </p>
        {opportunity.assigned_user ? (
          <p className="truncate" title={opportunity.assigned_user.full_name}>
            Responsable: {opportunity.assigned_user.full_name}
          </p>
        ) : (
          <p>Sin responsable</p>
        )}
      </div>

      <div className="mt-2.5 space-y-1.5 border-t border-slate-100 pt-2.5">
        <AppLink
          aria-label={`Ver detalle de la oportunidad de ${opportunity.customer.name}`}
          className="flex min-h-11 items-center justify-between border border-slate-300 px-2.5 py-1.5 text-xs font-semibold text-slate-700 outline-none transition-colors duration-150 hover:border-slate-400 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-amber-500 motion-reduce:transition-none"
          to={`/opportunities/${opportunity.id}`}
        >
          Ver detalle
          <svg aria-hidden="true" className="size-4" fill="none" viewBox="0 0 20 20">
            <path d="m7 4 6 6-6 6" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7" />
          </svg>
        </AppLink>

        {nextStatus ? (
          <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-1.5">
            <button
              aria-label={`Mover a ${nextStage?.singularLabel}`}
              className="min-h-11 border border-slate-300 px-2.5 py-1.5 text-left text-xs font-semibold text-slate-700 outline-none transition-colors duration-150 hover:border-slate-400 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-amber-500 disabled:cursor-wait disabled:opacity-50 motion-reduce:transition-none"
              disabled={isBusy}
              onClick={() => onMove(opportunity.id, nextStatus)}
              type="button"
            >
              {isBusy ? 'Actualizando…' : `Mover → ${nextStage?.singularLabel}`}
            </button>
            <button
              aria-label="Marcar como perdida"
              className="min-h-11 px-2.5 py-1.5 text-left text-xs font-medium text-red-700 outline-none transition-colors duration-150 hover:bg-red-50 hover:text-red-900 focus-visible:ring-2 focus-visible:ring-red-600 disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none"
              disabled={isBusy}
              onClick={() => onLose(opportunity.id)}
              type="button"
            >
              Marcar perdida
            </button>
          </div>
        ) : null}
      </div>
    </article>
  )
}
