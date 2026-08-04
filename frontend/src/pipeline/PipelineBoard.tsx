import {
  DragDropProvider,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  type DragEndEvent,
} from '@dnd-kit/react'

import { canMoveTo, isPipelineStatus, PIPELINE_STAGES } from './config'
import { PipelineColumn } from './PipelineColumn'
import type { PipelineDragData } from './OpportunityCard'
import type { OpportunitySummary, PipelineStatus } from './types'

const PIPELINE_SENSORS = [
  PointerSensor,
  KeyboardSensor.configure({ offset: { x: 280, y: 10 } }),
]

export function PipelineBoard({
  opportunities,
  busyOpportunityIds,
  onMove,
  onLose,
}: {
  opportunities: OpportunitySummary[]
  busyOpportunityIds: ReadonlySet<number>
  onMove: (opportunityId: number, targetStatus: PipelineStatus) => void
  onLose: (opportunityId: number) => void
}) {
  const visibleOpportunities = opportunities.filter(
    (opportunity): opportunity is OpportunitySummary & { status: PipelineStatus } =>
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
      <div
        aria-label="Etapas del pipeline. Desplazamiento horizontal disponible en pantallas pequeñas."
        className="max-w-full overflow-x-auto overscroll-x-contain pb-3"
        role="region"
        tabIndex={0}
      >
        <div className="grid min-w-[70rem] grid-cols-4 gap-3">
          {PIPELINE_STAGES.map((stage) => (
            <PipelineColumn
              busyOpportunityIds={busyOpportunityIds}
              key={stage.status}
              onLose={onLose}
              onMove={onMove}
              opportunities={visibleOpportunities.filter(
                (opportunity) => opportunity.status === stage.status,
              )}
              stage={stage}
            />
          ))}
        </div>
      </div>

      <DragOverlay dropAnimation={null}>
        {(source) => (
          <div className="w-64 border border-amber-500 bg-white px-3 py-2.5 text-sm font-semibold text-slate-950 shadow-xl">
            {(source.data as PipelineDragData | undefined)?.customerName ??
              'Oportunidad'}
          </div>
        )}
      </DragOverlay>
    </DragDropProvider>
  )
}
