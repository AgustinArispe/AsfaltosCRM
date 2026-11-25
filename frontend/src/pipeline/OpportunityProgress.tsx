import { useId } from 'react'
import { formatDateTime, formatStageDuration } from '../shared/formatters'
import { Icon } from '../shared/Icon'
import { OPPORTUNITY_STATUS_LABELS, opportunityStatusColorClass, PIPELINE_STAGES } from './config'
import type { OpportunityDetail, OpportunityStatus } from './types'

const LOST_STEP = {
  status: 'PERDIDA',
  label: OPPORTUNITY_STATUS_LABELS.PERDIDA,
  icon: 'x-circle',
} as const

function activePipelineStatus(status: OpportunityStatus): OpportunityStatus {
  return status === 'NEGOCIACION' ? 'COTIZADA' : status
}

export function OpportunityProgress({ opportunity }: { opportunity: OpportunityDetail }) {
  const titleId = useId()
  const currentStatus = activePipelineStatus(opportunity.status)
  const lost = currentStatus === 'PERDIDA'
  const duration = formatStageDuration(opportunity.current_status_entered_at)
  const dates = new Map<OpportunityStatus, string>()
  let lastOpenStatus: OpportunityStatus = 'NUEVA'
  let lossFrom: OpportunityStatus | null = null

  for (const entry of opportunity.history) {
    // A legacy negotiation can establish progress, but isn't the date of the quote.
    if (entry.to_status !== 'NEGOCIACION') dates.set(entry.to_status, entry.changed_at)
    if (entry.to_status === 'PERDIDA') lossFrom = entry.from_status
    else if (entry.to_status !== 'GANADA') lastOpenStatus = entry.to_status
  }
  if (opportunity.status !== 'NEGOCIACION') {
    dates.set(currentStatus, opportunity.current_status_entered_at)
  }
  dates.set('NUEVA', opportunity.created_at)

  const steps = lost ? [...PIPELINE_STAGES.slice(0, -1), LOST_STEP] : PIPELINE_STAGES
  const completedThrough = PIPELINE_STAGES.findIndex(
    (stage) =>
      stage.status === (lost ? activePipelineStatus(lossFrom ?? lastOpenStatus) : currentStatus),
  )

  return (
    <section aria-labelledby={titleId} className='opportunity-progress'>
      <div className='opportunity-progress__heading'>
        <h3 className='opportunity-progress__title' id={titleId}>
          Avance de la oportunidad
        </h3>
        <p className='opportunity-progress__elapsed'>
          <Icon name='clock' />
          <span>
            En {OPPORTUNITY_STATUS_LABELS[opportunity.status]} desde{' '}
            <strong>{duration === 'Hoy' ? 'hoy' : `hace ${duration}`}</strong>
          </span>
        </p>
      </div>
      <ol aria-labelledby={titleId} className='opportunity-progress__steps'>
        {steps.map((stage, index) => {
          const isCurrent = stage.status === currentStatus
          const progress = isCurrent
            ? 'current'
            : index <= completedThrough
              ? 'complete'
              : 'pending'
          const connectorComplete =
            index > 0 && index - 1 <= completedThrough && progress !== 'pending'
          const date = progress === 'pending' ? undefined : dates.get(stage.status)
          const timestamp = date ? formatDateTime(date) : null
          return (
            <li
              aria-current={isCurrent ? 'step' : undefined}
              className={`opportunity-progress__step ${opportunityStatusColorClass(stage.status)}`}
              data-connected={connectorComplete ? 'true' : undefined}
              data-progress={progress}
              key={stage.status}
            >
              <span className='opportunity-progress__marker' aria-hidden='true'>
                <Icon name={progress === 'complete' ? 'check' : stage.icon} />
              </span>
              <span className='opportunity-progress__label'>
                {stage.label}
                {progress === 'complete' ? <span className='sr-only'>, completada</span> : null}
              </span>
              {timestamp ? (
                <time className='opportunity-progress__date' dateTime={date} title={timestamp}>
                  {stage.status === 'NUEVA' ? timestamp : timestamp.split(',')[0]}
                </time>
              ) : (
                <span className='opportunity-progress__date'>
                  {progress === 'pending' ? (lost ? 'Sin completar' : 'Pendiente') : 'Sin fecha'}
                </span>
              )}
            </li>
          )
        })}
      </ol>
    </section>
  )
}
