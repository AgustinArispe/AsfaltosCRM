import type {
  LeadSource,
  LossReason,
  OpportunityStatus,
  PipelineStatus,
} from './types'

export type PipelineStage = {
  status: PipelineStatus
  label: string
  singularLabel: string
  nextStatus: PipelineStatus | null
  accentClassName: string
  countClassName: string
}

export const PIPELINE_STAGES: readonly PipelineStage[] = [
  {
    status: 'NUEVA',
    label: 'Nuevos',
    singularLabel: 'Nueva',
    nextStatus: 'COTIZADA',
    accentClassName: 'border-t-sky-500',
    countClassName: 'bg-sky-100 text-sky-800',
  },
  {
    status: 'COTIZADA',
    label: 'Cotizados',
    singularLabel: 'Cotizada',
    nextStatus: 'NEGOCIACION',
    accentClassName: 'border-t-amber-500',
    countClassName: 'bg-amber-100 text-amber-900',
  },
  {
    status: 'NEGOCIACION',
    label: 'Negociación',
    singularLabel: 'Negociación',
    nextStatus: 'GANADA',
    accentClassName: 'border-t-violet-500',
    countClassName: 'bg-violet-100 text-violet-800',
  },
  {
    status: 'GANADA',
    label: 'Ganados',
    singularLabel: 'Ganada',
    nextStatus: null,
    accentClassName: 'border-t-emerald-600',
    countClassName: 'bg-emerald-100 text-emerald-800',
  },
] as const

export const PIPELINE_STATUS_SET = new Set<PipelineStatus>(
  PIPELINE_STAGES.map((stage) => stage.status),
)

export const STAGE_BY_STATUS = new Map(
  PIPELINE_STAGES.map((stage) => [stage.status, stage]),
)

export const OPPORTUNITY_STATUS_LABELS: Record<OpportunityStatus, string> = {
  NUEVA: 'Nueva',
  COTIZADA: 'Cotizada',
  NEGOCIACION: 'Negociación',
  GANADA: 'Ganada',
  PERDIDA: 'Perdida',
}

export const OPPORTUNITY_STATUS_BADGE_CLASSES: Record<
  OpportunityStatus,
  string
> = {
  NUEVA: 'border-sky-200 bg-sky-50 text-sky-800',
  COTIZADA: 'border-amber-200 bg-amber-50 text-amber-900',
  NEGOCIACION: 'border-violet-200 bg-violet-50 text-violet-800',
  GANADA: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  PERDIDA: 'border-red-200 bg-red-50 text-red-800',
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

export function canMoveTo(
  from: PipelineStatus,
  to: PipelineStatus,
): boolean {
  return STAGE_BY_STATUS.get(from)?.nextStatus === to
}
