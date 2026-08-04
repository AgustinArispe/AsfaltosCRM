import { useDroppable } from '@dnd-kit/react'

import type { PipelineStage } from './config'
import { OpportunityCard } from './OpportunityCard'
import type { OpportunitySummary, PipelineStatus } from './types'

export function PipelineColumn({
  stage,
  opportunities,
  busyOpportunityIds,
  onMove,
  onLose,
}: {
  stage: PipelineStage
  opportunities: (OpportunitySummary & { status: PipelineStatus })[]
  busyOpportunityIds: ReadonlySet<number>
  onMove: (opportunityId: number, targetStatus: PipelineStatus) => void
  onLose: (opportunityId: number) => void
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
        'flex min-h-[28rem] min-w-0 flex-col border border-t-2 border-slate-200 bg-slate-50',
        stage.accentClassName,
        isDropTarget ? 'ring-2 ring-amber-500 ring-offset-2' : '',
      ].join(' ')}
      data-stage={stage.status}
      ref={ref}
    >
      <header className="flex min-h-12 items-center justify-between gap-3 border-b border-slate-200 bg-white px-3 py-2.5">
        <h2 className="text-sm font-semibold text-slate-900" id={headingId}>
          {stage.label}
        </h2>
        <span
          aria-label={`${opportunities.length} ${opportunities.length === 1 ? 'oportunidad' : 'oportunidades'}`}
          className={`min-w-7 px-2 py-0.5 text-center text-xs font-bold tabular-nums ${stage.countClassName}`}
        >
          {opportunities.length}
        </span>
      </header>

      <div className="flex flex-1 flex-col gap-2 p-2.5">
        {opportunities.length > 0 ? (
          opportunities.map((opportunity) => (
            <OpportunityCard
              isBusy={busyOpportunityIds.has(opportunity.id)}
              key={opportunity.id}
              onLose={onLose}
              onMove={onMove}
              opportunity={opportunity}
            />
          ))
        ) : (
          <p className="px-2 py-8 text-center text-sm text-slate-500">
            No hay oportunidades
          </p>
        )}
      </div>
    </section>
  )
}
