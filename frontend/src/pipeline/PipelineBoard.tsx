import {
  DragDropProvider,
  type DragEndEvent,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
} from '@dnd-kit/react'

import { canMoveTo, isPipelineStatus, PIPELINE_STAGES } from './config'
import type { PipelineDragData } from './OpportunityCard'
import { PipelineColumn } from './PipelineColumn'
import type { OpportunitySummary, PipelineStatus } from './types'

const PIPELINE_SENSORS = [
  PointerSensor,
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
}: {
  opportunities: OpportunitySummary[]
  busyOpportunityIds: ReadonlySet<number>
  onMove: (opportunityId: number, targetStatus: PipelineStatus) => void
  onOpenDetail: (opportunityId: number) => void
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
      <section
        aria-label='Etapas del pipeline. Desplazamiento horizontal disponible en pantallas pequeñas.'
        className='max-w-full overflow-x-auto overscroll-x-contain pb-2 outline-none focus-visible:ring-2 focus-visible:ring-slate-500'
      >
        <div className='grid min-w-[68rem] grid-cols-4 gap-2.5'>
          {PIPELINE_STAGES.map((stage) => (
            <PipelineColumn
              busyOpportunityIds={busyOpportunityIds}
              key={stage.status}
              onMove={onMove}
              onOpenDetail={onOpenDetail}
              opportunities={visibleOpportunities.filter(
                (opportunity) => opportunity.status === stage.status,
              )}
              stage={stage}
            />
          ))}
        </div>
      </section>

      <DragOverlay dropAnimation={null}>
        {(source) => (
          <div className='w-64 rounded-[5px] border border-slate-400 bg-white px-3 py-3 text-sm font-semibold text-slate-950 shadow-lg'>
            {(source.data as PipelineDragData | undefined)?.customerName ?? 'Oportunidad'}
          </div>
        )}
      </DragOverlay>
    </DragDropProvider>
  )
}
