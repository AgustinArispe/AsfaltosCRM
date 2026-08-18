import { PointerActivationConstraints } from '@dnd-kit/dom'
import {
  DragDropProvider,
  type DragEndEvent,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
} from '@dnd-kit/react'

import { opportunitiesForStage } from './board-state'
import { canMoveTo, isPipelineStatus, PIPELINE_STAGES } from './config'
import type { PipelineDragData } from './OpportunityCard'
import { PipelineColumn } from './PipelineColumn'
import type { OpportunitySummary, PipelineStatus } from './types'

const PIPELINE_SENSORS = [
  PointerSensor.configure({
    activationConstraints: [new PointerActivationConstraints.Distance({ value: 6 })],
  }),
  KeyboardSensor.configure({
    offset: { x: 280, y: 10 },
    keyboardCodes: {
      start: ['Space'],
      cancel: ['Escape'],
      end: ['Space', 'Enter', 'Tab'],
      up: ['ArrowUp'],
      down: ['ArrowDown'],
      left: ['ArrowLeft'],
      right: ['ArrowRight'],
    },
  }),
]

export function PipelineBoard({
  opportunities,
  busyOpportunityIds,
  onMove,
  onOpenDetail,
  showStageAge,
  selectedOpportunityId,
}: {
  opportunities: OpportunitySummary[]
  busyOpportunityIds: ReadonlySet<number>
  onMove: (opportunityId: number, targetStatus: PipelineStatus) => void
  onOpenDetail: (opportunityId: number) => void
  showStageAge: boolean
  selectedOpportunityId?: number
}) {
  const visibleOpportunities = opportunities.filter((opportunity) =>
    isPipelineStatus(opportunity.status),
  )

  const handleDragEnd = (event: DragEndEvent) => {
    if (event.canceled) return
    const source = event.operation.source
    const targetStatus = String(event.operation.target?.id ?? '')
    const dragData = source?.data as PipelineDragData | undefined

    if (
      !dragData ||
      !isPipelineStatus(targetStatus) ||
      !canMoveTo(dragData.fromStatus, targetStatus) ||
      dragData.toStatus !== targetStatus
    ) {
      return
    }
    onMove(dragData.opportunityId, targetStatus)
  }

  return (
    <DragDropProvider onDragEnd={handleDragEnd} sensors={PIPELINE_SENSORS}>
      <section
        aria-label='Etapas del pipeline. Desplazamiento horizontal disponible en pantallas pequeñas.'
        className='pipeline-board'
      >
        <div className='pipeline-board__grid'>
          {PIPELINE_STAGES.map((stage) => (
            <PipelineColumn
              busyOpportunityIds={busyOpportunityIds}
              key={stage.status}
              onOpenDetail={onOpenDetail}
              opportunities={opportunitiesForStage(visibleOpportunities, stage.status)}
              showStageAge={showStageAge}
              stage={stage}
              selectedOpportunityId={selectedOpportunityId}
            />
          ))}
        </div>
      </section>

      <DragOverlay dropAnimation={null}>
        {(source) => (
          <div className='ui-surface-raised w-64 px-3 py-3 text-sm font-semibold text-[var(--text-primary)]'>
            {(source.data as PipelineDragData | undefined)?.customerName ?? 'Oportunidad'}
          </div>
        )}
      </DragOverlay>
    </DragDropProvider>
  )
}
