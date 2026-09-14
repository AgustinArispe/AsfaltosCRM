import { useDraggable } from '@dnd-kit/react'

import { LegendaryBadge } from '../customers/LegendaryBadge'
import { Icon } from '../shared/Icon'
import { customerIdentity } from './board-state'
import { opportunityStatusColorClass, SOURCE_LABELS, STAGE_BY_STATUS } from './config'
import type { OpportunitySummary, PipelineStatus } from './types'

export type PipelineDragData = {
  opportunityId: number
  customerName: string
  supportingName: string | null
  isLegendary: boolean
  fromStatus: PipelineStatus
  statusLabel: string
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
  const stage = STAGE_BY_STATUS.get(opportunity.status)
  const canChangeStage = Boolean(stage?.nextStatus || stage?.previousStatus)
  const isDraggable = canChangeStage && !isBusy
  const identity = customerIdentity(opportunity.customer)
  const { ref, isDragging } = useDraggable<PipelineDragData>({
    id: opportunity.id,
    type: 'OPPORTUNITY',
    disabled: !isDraggable,
    data: canChangeStage
      ? {
          opportunityId: opportunity.id,
          customerName: identity.primary,
          supportingName: identity.supporting,
          isLegendary: Boolean(opportunity.customer.is_legendary),
          fromStatus: opportunity.status,
          statusLabel: STAGE_BY_STATUS.get(opportunity.status)?.label ?? opportunity.status,
        }
      : undefined,
  })

  return (
    <article
      aria-busy={isBusy}
      className={[
        'pipeline-card',
        opportunityStatusColorClass(opportunity.status),
        isSelected ? 'pipeline-card--selected' : '',
        isDragging ? 'pipeline-card--dragging' : '',
        isBusy ? 'pipeline-card--busy' : '',
        !canChangeStage ? 'pipeline-card--terminal' : '',
      ].join(' ')}
      data-opportunity-id={opportunity.id}
    >
      <button
        aria-current={isSelected ? 'true' : undefined}
        aria-describedby={isBusy ? `pipeline-card-pending-${opportunity.id}` : undefined}
        aria-label={`Abrir oportunidad de ${identity.primary}, origen ${SOURCE_LABELS[opportunity.source]}, estado ${STAGE_BY_STATUS.get(opportunity.status)?.label ?? opportunity.status}${isDraggable ? '. Se puede arrastrar a una etapa permitida.' : '. No tiene movimientos disponibles.'}`}
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
        <span className='pipeline-card__topline'>
          <span className='pipeline-card__identity-block'>
            <span className='pipeline-card__identity' title={identity.primary}>
              {identity.primary}
            </span>
            {identity.supporting ? (
              <span className='pipeline-card__contact' title={identity.supporting}>
                {identity.supporting}
              </span>
            ) : null}
          </span>
          <Icon className='pipeline-card__chevron' name='chevron-right' />
        </span>
        <span className='pipeline-card__meta'>
          <span className='pipeline-card__source'>{SOURCE_LABELS[opportunity.source]}</span>
          {showStageAge ? (
            <span className='pipeline-card__stage-age'>
              En etapa: {formatStageAge(opportunity.current_status_entered_at)}
            </span>
          ) : null}
          {opportunity.customer.is_legendary ? <LegendaryBadge /> : null}
        </span>
        <span
          className='pipeline-card__pending'
          id={`pipeline-card-pending-${opportunity.id}`}
          role={isBusy ? 'status' : undefined}
        >
          <span aria-hidden='true' className='pipeline-card__spinner' />
          Actualizando…
        </span>
      </button>
    </article>
  )
}

function formatStageAge(value: string): string {
  const elapsedDays = Math.floor(Math.max(0, Date.now() - Date.parse(value)) / 86_400_000)
  if (elapsedDays < 1) return 'hoy'
  return `${elapsedDays} ${elapsedDays === 1 ? 'día' : 'días'}`
}
