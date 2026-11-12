import { useEffect, useState } from 'react'
import { Button } from '../shared/Button'
import { Icon } from '../shared/Icon'
import { Modal } from '../shared/Modal'
import { opportunityStatusColorClass, PIPELINE_STAGES, STAGE_BY_STATUS } from './config'
import { StageNoteField } from './StageNoteField'
import { StageProvinceField } from './StageProvinceField'
import type { PipelineStatus } from './types'

export type PendingStageTransition = {
  opportunityId: number
  fromStatus: PipelineStatus
  targetStatus: PipelineStatus
}

export function stageTransitionConfirmationCopy(
  fromStatus: PipelineStatus,
  targetStatus: PipelineStatus,
): { description: string; actionLabel: string } {
  const destination = STAGE_BY_STATUS.get(targetStatus)?.label ?? targetStatus
  if (targetStatus === 'GANADA') {
    return {
      description: '¿Querés marcar esta oportunidad como Ganada?',
      actionLabel: 'Marcar como Ganada',
    }
  }

  const fromIndex = PIPELINE_STAGES.findIndex((stage) => stage.status === fromStatus)
  const targetIndex = PIPELINE_STAGES.findIndex((stage) => stage.status === targetStatus)
  const isBackward = targetIndex < fromIndex

  return isBackward
    ? {
        description: `¿Querés volver esta oportunidad a ${destination}?`,
        actionLabel: `Volver a ${destination}`,
      }
    : {
        description: `¿Querés avanzar esta oportunidad a ${destination}?`,
        actionLabel: `Avanzar a ${destination}`,
      }
}

export function StageTransitionConfirmationModal({
  transition,
  isPending,
  onCancel,
  onConfirm,
  error,
  customerProvince,
}: {
  transition: PendingStageTransition | null
  isPending: boolean
  onCancel: () => void
  onConfirm: (note: string, province?: string) => void
  error?: string | null
  customerProvince?: string | null
}) {
  const [note, setNote] = useState('')
  const [province, setProvince] = useState('')
  useEffect(() => {
    if (!transition) {
      setNote('')
      setProvince('')
    }
  }, [transition])
  if (!transition) return null
  const targetStatus = transition?.targetStatus ?? 'NUEVA'
  const stage = STAGE_BY_STATUS.get(targetStatus)
  const copy = transition
    ? stageTransitionConfirmationCopy(transition.fromStatus, transition.targetStatus)
    : null

  return (
    <Modal
      closeDisabled={isPending}
      description={copy?.description}
      isOpen={transition !== null}
      onClose={onCancel}
      title='Confirmar cambio de etapa'
    >
      <div className='space-y-4 px-5 py-5 sm:px-6'>
        {error ? (
          <p className='text-sm text-[var(--destructive-text)]' role='alert'>
            {error}
          </p>
        ) : null}
        <div
          className={`flex items-center gap-3 rounded-[var(--radius-control)] border border-[var(--opportunity-stage-border)] bg-[var(--opportunity-stage-surface)] px-3.5 py-3 ${opportunityStatusColorClass(targetStatus)}`}
        >
          <span
            aria-hidden='true'
            className='grid size-9 shrink-0 place-items-center rounded-full bg-[var(--opportunity-stage-solid)] text-[var(--opportunity-stage-on-solid)]'
          >
            <Icon className='size-[1.05rem]' name={stage?.icon ?? 'document'} />
          </span>
          <div>
            <p className='text-sm font-semibold text-[var(--opportunity-stage-text)]'>
              {stage?.label ?? targetStatus}
            </p>
            <p className='mt-0.5 text-xs text-[var(--text-secondary)]'>
              El cambio se aplicará al confirmar.
            </p>
          </div>
        </div>
        <StageNoteField disabled={isPending} onChange={setNote} value={note} />
        {targetStatus === 'GANADA' ? (
          <StageProvinceField
            currentProvince={customerProvince}
            disabled={isPending}
            onChange={setProvince}
            value={province}
          />
        ) : null}
      </div>
      <footer className='flex flex-wrap justify-end gap-2 border-t border-[var(--divider)] px-5 py-4 sm:px-6'>
        <Button
          data-modal-initial-focus
          disabled={isPending}
          onClick={onCancel}
          variant='secondary'
        >
          Cancelar
        </Button>
        <Button
          disabled={!note.trim()}
          isLoading={isPending}
          onClick={() => onConfirm(note.trim(), province.trim() || undefined)}
          variant='primary'
        >
          {copy?.actionLabel ?? 'Confirmar cambio'}
        </Button>
      </footer>
    </Modal>
  )
}
