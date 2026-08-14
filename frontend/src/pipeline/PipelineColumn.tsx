import { useDroppable } from '@dnd-kit/react'

import type { PipelineStage } from './config'
import { OpportunityCard } from './OpportunityCard'
import type { OpportunitySummary, PipelineStatus } from './types'

export function PipelineColumn({
  stage,
  opportunities,
  busyOpportunityIds,
  onOpenDetail,
  showStageAge,
}: {
  stage: PipelineStage
  opportunities: (OpportunitySummary & { status: PipelineStatus })[]
  busyOpportunityIds: ReadonlySet<number>
  onOpenDetail: (opportunityId: number) => void
  showStageAge: boolean
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
            />
          ))
        ) : (
          <p className='px-2 py-8 text-center text-sm text-slate-500'>No hay oportunidades</p>
        )}
      </div>
    </section>
  )
}
