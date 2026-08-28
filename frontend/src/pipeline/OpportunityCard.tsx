import { useDraggable } from '@dnd-kit/react'

import { LegendaryBadge } from '../customers/LegendaryBadge'
import { customerIdentity } from './board-state'
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
  onOpenDetail,
  showStageAge,
  isSelected = false,
}: {
  opportunity: OpportunitySummary & { status: PipelineStatus }
  isBusy: boolean
  onOpenDetail: (opportunityId: number) => void
  showStageAge: boolean
  isSelected?: boolean
}) {
  const nextStatus = STAGE_BY_STATUS.get(opportunity.status)?.nextStatus ?? null
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
  const identity = customerIdentity(opportunity.customer)

  return (
    <article
      aria-busy={isBusy}
      className={[
        'pipeline-card',
        isSelected ? 'pipeline-card--selected' : '',
        isDragging ? 'opacity-40' : '',
      ].join(' ')}
      data-opportunity-id={opportunity.id}
    >
      <button
        aria-current={isSelected ? 'true' : undefined}
        aria-label={`Abrir oportunidad de ${identity.primary}, origen ${SOURCE_LABELS[opportunity.source]}${isDraggable ? '. Se puede arrastrar a la siguiente etapa.' : ''}`}
        className={[
          'pipeline-card__button',
          isDraggable ? 'cursor-grab active:cursor-grabbing' : 'cursor-pointer',
        ].join(' ')}
        disabled={isBusy}
        onClick={() => {
          if (!isDragging) onOpenDetail(opportunity.id)
        }}
        ref={isDraggable ? ref : undefined}
        type='button'
      >
        <span className='pipeline-card__identity' title={identity.primary}>
          {identity.primary}
        </span>
        {identity.supporting ? (
          <span className='pipeline-card__contact' title={identity.supporting}>
            {identity.supporting}
          </span>
        ) : null}
        <span className='pipeline-card__meta'>
          <span className='pipeline-card__source'>{SOURCE_LABELS[opportunity.source]}</span>
          {opportunity.customer.is_legendary ? <LegendaryBadge /> : null}
        </span>
        {showStageAge ? (
          <span className='pipeline-card__stage-age'>
            En etapa: {formatStageAge(opportunity.current_status_entered_at)}
          </span>
        ) : null}
      </button>
    </article>
  )
}

function formatStageAge(value: string): string {
  const elapsedDays = Math.floor(Math.max(0, Date.now() - Date.parse(value)) / 86_400_000)
  if (elapsedDays < 1) return 'hoy'
  return `${elapsedDays} ${elapsedDays === 1 ? 'día' : 'días'}`
}
