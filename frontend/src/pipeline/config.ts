import type { BadgeTone } from '../shared/Badge'
import type { IconName } from '../shared/Icon'
import type { LeadSource, LossReason, OpportunityStatus, PipelineStatus } from './types'

export type PipelineStage = {
  status: PipelineStatus
  label: string
  singularLabel: string
  icon: IconName
  nextStatus: PipelineStatus | null
  previousStatus: PipelineStatus | null
  tone: 'neutral' | 'success'
}

export const PIPELINE_STAGES: readonly PipelineStage[] = [
  {
    status: 'NUEVA',
    label: 'Nueva',
    singularLabel: 'Nueva',
    icon: 'inbox',
    nextStatus: 'PARA_COTIZAR',
    previousStatus: null,
    tone: 'neutral',
  },
  {
    status: 'PARA_COTIZAR',
    label: 'Para cotizar',
    singularLabel: 'Para cotizar',
    icon: 'pencil',
    nextStatus: 'COTIZADA',
    previousStatus: null,
    tone: 'neutral',
  },
  {
    status: 'COTIZADA',
    label: 'Cotizada',
    singularLabel: 'Cotizada',
    icon: 'document',
    nextStatus: 'GANADA',
    previousStatus: 'PARA_COTIZAR',
    tone: 'neutral',
  },
  {
    status: 'GANADA',
    label: 'Ganada',
    singularLabel: 'Ganada',
    icon: 'trophy',
    nextStatus: null,
    previousStatus: 'COTIZADA',
    tone: 'success',
  },
] as const

export const PIPELINE_STATUS_SET = new Set<PipelineStatus>(
  PIPELINE_STAGES.map((stage) => stage.status),
)

export const STAGE_BY_STATUS = new Map(PIPELINE_STAGES.map((stage) => [stage.status, stage]))

export const OPPORTUNITY_STATUS_LABELS: Record<OpportunityStatus, string> = {
  NUEVA: 'Nueva',
  PARA_COTIZAR: 'Para cotizar',
  COTIZADA: 'Cotizada',
  NEGOCIACION: 'Negociación (histórico)',
  GANADA: 'Ganada',
  PERDIDA: 'Pérdida',
}

export const OPPORTUNITY_STATUS_TONES: Record<OpportunityStatus, BadgeTone> = {
  NUEVA: 'new',
  PARA_COTIZAR: 'negotiation',
  COTIZADA: 'quoted',
  NEGOCIACION: 'negotiation',
  GANADA: 'won',
  PERDIDA: 'lost',
}

export const OPPORTUNITY_STATUS_COLOR_CLASSES: Record<OpportunityStatus, string> = {
  NUEVA: 'opportunity-stage-tone--nueva',
  PARA_COTIZAR: 'opportunity-stage-tone--negociacion',
  COTIZADA: 'opportunity-stage-tone--cotizada',
  NEGOCIACION: 'opportunity-stage-tone--negociacion',
  GANADA: 'opportunity-stage-tone--ganada',
  PERDIDA: 'opportunity-stage-tone--perdida',
}

export function opportunityStatusColorClass(status: OpportunityStatus): string {
  return `opportunity-stage-tone ${OPPORTUNITY_STATUS_COLOR_CLASSES[status]}`
}

export const LOSS_REASON_LABELS: Record<LossReason, string> = {
  PRECIO: 'Precio',
  SIN_RESPUESTA: 'Sin respuesta',
  COMPETENCIA: 'Competencia',
  PROYECTO_CANCELADO: 'Proyecto cancelado',
  OTRO: 'Otro',
}

export const LOSS_REASON_OPTIONS: readonly {
  value: LossReason
  label: string
}[] = [
  { value: 'PRECIO', label: LOSS_REASON_LABELS.PRECIO },
  { value: 'SIN_RESPUESTA', label: LOSS_REASON_LABELS.SIN_RESPUESTA },
  { value: 'COMPETENCIA', label: LOSS_REASON_LABELS.COMPETENCIA },
  {
    value: 'PROYECTO_CANCELADO',
    label: LOSS_REASON_LABELS.PROYECTO_CANCELADO,
  },
  { value: 'OTRO', label: LOSS_REASON_LABELS.OTRO },
] as const

export const SOURCE_LABELS: Record<LeadSource, string> = {
  WEB: 'Web',
  WHATSAPP: 'WhatsApp',
  REFERIDO: 'Manual',
  INSTAGRAM: 'Instagram',
}

export const SOURCE_OPTIONS: readonly { value: LeadSource; label: string }[] = (
  Object.entries(SOURCE_LABELS) as [LeadSource, string][]
).map(([value, label]) => ({ value, label }))

export function isPipelineStatus(value: string): value is PipelineStatus {
  return PIPELINE_STATUS_SET.has(value as PipelineStatus)
}

export function canMoveTo(from: PipelineStatus, to: PipelineStatus): boolean {
  const stage = STAGE_BY_STATUS.get(from)
  return stage?.nextStatus === to || stage?.previousStatus === to
}

export function isBackwardMove(from: PipelineStatus, to: PipelineStatus): boolean {
  return STAGE_BY_STATUS.get(from)?.previousStatus === to
}
