import type { BadgeTone } from '../shared/Badge'
import type { LeadSource, LossReason, OpportunityStatus, PipelineStatus } from './types'

export type PipelineStage = {
  status: PipelineStatus
  label: string
  singularLabel: string
  nextStatus: PipelineStatus | null
  tone: 'neutral' | 'success'
}

export const PIPELINE_STAGES: readonly PipelineStage[] = [
  {
    status: 'NUEVA',
    label: 'Nueva',
    singularLabel: 'Nueva',
    nextStatus: 'COTIZADA',
    tone: 'neutral',
  },
  {
    status: 'COTIZADA',
    label: 'Cotizada',
    singularLabel: 'Cotizada',
    nextStatus: 'NEGOCIACION',
    tone: 'neutral',
  },
  {
    status: 'NEGOCIACION',
    label: 'Negociación',
    singularLabel: 'Negociación',
    nextStatus: 'GANADA',
    tone: 'neutral',
  },
  {
    status: 'GANADA',
    label: 'Ganada',
    singularLabel: 'Ganada',
    nextStatus: null,
    tone: 'success',
  },
] as const

export const PIPELINE_STATUS_SET = new Set<PipelineStatus>(
  PIPELINE_STAGES.map((stage) => stage.status),
)

export const STAGE_BY_STATUS = new Map(PIPELINE_STAGES.map((stage) => [stage.status, stage]))

export const OPPORTUNITY_STATUS_LABELS: Record<OpportunityStatus, string> = {
  NUEVA: 'Nueva',
  COTIZADA: 'Cotizada',
  NEGOCIACION: 'Negociación',
  GANADA: 'Ganada',
  PERDIDA: 'Perdida',
}

export const OPPORTUNITY_STATUS_TONES: Record<OpportunityStatus, BadgeTone> = {
  NUEVA: 'new',
  COTIZADA: 'quoted',
  NEGOCIACION: 'negotiation',
  GANADA: 'won',
  PERDIDA: 'lost',
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
}

export function isPipelineStatus(value: string): value is PipelineStatus {
  return PIPELINE_STATUS_SET.has(value as PipelineStatus)
}

export function canMoveTo(from: PipelineStatus, to: PipelineStatus): boolean {
  return STAGE_BY_STATUS.get(from)?.nextStatus === to
}
