import { useDroppable } from '@dnd-kit/react'
import { EmptyState } from '../shared/StatusStates'
import type { PipelineStage } from './config'
import { OpportunityCard } from './OpportunityCard'
import type { OpportunitySummary, PipelineStatus } from './types'

export function PipelineColumn({
  stage,
  opportunities,
  busyOpportunityIds,
  onOpenDetail,
  showStageAge,
  selectedOpportunityId,
}: {
  stage: PipelineStage
  opportunities: (OpportunitySummary & { status: PipelineStatus })[]
  busyOpportunityIds: ReadonlySet<number>
  onOpenDetail: (opportunityId: number) => void
  showStageAge: boolean
  selectedOpportunityId?: number
}) {
  const { ref, isDropTarget } = useDroppable({
    id: stage.status,
    accept: stage.status,
  })
  const headingId = `pipeline-stage-${stage.status.toLowerCase()}`

  return (
    <section
      aria-labelledby={headingId}
      className={[
        'pipeline-column',
        stage.tone === 'success' ? 'pipeline-column--success' : '',
        isDropTarget ? 'pipeline-column--drop-target' : '',
      ].join(' ')}
      data-stage={stage.status}
      ref={ref}
    >
      <header className='pipeline-column__header'>
        <h2 className='text-sm font-semibold text-[var(--text-primary)]' id={headingId}>
          {stage.label}
        </h2>
        <span className='pipeline-column__count'>
          {opportunities.length}
          <span className='sr-only'>
            {' '}
            {opportunities.length === 1 ? 'oportunidad' : 'oportunidades'}
          </span>
        </span>
      </header>

      <div className='pipeline-column__cards'>
        {opportunities.length > 0 ? (
          opportunities.map((opportunity) => (
            <OpportunityCard
              isBusy={busyOpportunityIds.has(opportunity.id)}
              key={opportunity.id}
              onOpenDetail={onOpenDetail}
              opportunity={opportunity}
              showStageAge={showStageAge}
              isSelected={opportunity.id === selectedOpportunityId}
            />
          ))
        ) : (
          <EmptyState
            description='Las oportunidades aparecerán aquí al ingresar en esta etapa.'
            icon='inbox'
            size='small'
            title='Sin oportunidades'
          />
        )}
      </div>
    </section>
  )
}
