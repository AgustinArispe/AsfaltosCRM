import { useDraggable } from '@dnd-kit/react'

import { LegendaryBadge } from '../customers/LegendaryBadge'
import { Badge } from '../shared/Badge'
import { STAGE_BY_STATUS, SOURCE_LABELS } from './config'
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
  onOpenDetail,
}: {
  opportunity: OpportunitySummary & { status: PipelineStatus }
  isBusy: boolean
  onMove: (opportunityId: number, targetStatus: PipelineStatus) => void
  onOpenDetail: (opportunityId: number) => void
}) {
  const stage = STAGE_BY_STATUS.get(opportunity.status)
  const nextStatus = stage?.nextStatus ?? null
  const nextStage = nextStatus ? STAGE_BY_STATUS.get(nextStatus) : null
  const isDraggable = Boolean(nextStatus) && !isBusy
  const { ref, isDragging } = useDraggable<PipelineDragData>({
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
  const primaryName = opportunity.customer.company ?? opportunity.customer.name
  const contactName = opportunity.customer.company ? opportunity.customer.name : null

  return (
    <article
      aria-busy={isBusy}
      className={[
        'overflow-hidden rounded-[5px] border border-l-2 border-slate-200 bg-white shadow-[0_1px_2px_rgb(15_23_42_/_0.04)]',
        stage?.cardAccentClassName ?? '',
        isDragging ? 'opacity-40' : '',
      ].join(' ')}
      data-opportunity-id={opportunity.id}
    >
      <button
        aria-label={`Abrir detalle de la oportunidad de ${opportunity.customer.name}${isDraggable ? '. También se puede arrastrar a la siguiente etapa.' : ''}`}
        className={[
          'block w-full touch-none px-3 py-3 text-left outline-none transition-colors duration-150 hover:bg-slate-50 focus-visible:bg-slate-50 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-slate-500 motion-reduce:transition-none',
          isDraggable ? 'cursor-grab active:cursor-grabbing' : 'cursor-pointer',
        ].join(' ')}
        disabled={isBusy}
        onClick={() => {
          if (!isDragging) onOpenDetail(opportunity.id)
        }}
        ref={isDraggable ? ref : undefined}
        type="button"
      >
        <span className="block truncate text-sm font-semibold leading-5 text-slate-950" title={primaryName}>
          {primaryName}
        </span>
        {contactName ? (
          <span className="mt-0.5 block truncate text-xs leading-5 text-slate-600" title={contactName}>
            {contactName}
          </span>
        ) : null}
        <span className="mt-2 flex flex-wrap items-center gap-1.5">
          <Badge tone="neutral">{SOURCE_LABELS[opportunity.source]}</Badge>
          {opportunity.customer.legendary_historical_override ? <LegendaryBadge /> : null}
        </span>
      </button>

      {nextStatus ? (
        <div className="border-t border-slate-100 px-2 py-1">
          <button
            aria-label={`Mover a ${nextStage?.singularLabel}: ${opportunity.customer.name}`}
            className="ui-pressable min-h-11 rounded-[4px] px-2 text-xs font-medium text-slate-500 outline-none hover:bg-slate-100 hover:text-slate-900 focus-visible:ring-2 focus-visible:ring-slate-500 disabled:cursor-wait disabled:opacity-45"
            disabled={isBusy}
            onClick={() => onMove(opportunity.id, nextStatus)}
            type="button"
          >
            {isBusy ? 'Actualizando…' : `Mover a ${nextStage?.singularLabel}`}
          </button>
        </div>
      ) : null}
    </article>
  )
}
