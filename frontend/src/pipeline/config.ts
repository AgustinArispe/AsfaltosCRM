import type {
  LeadSource,
  LossReason,
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

export const LOSS_REASON_OPTIONS: readonly {
  value: LossReason
  label: string
}[] = [
  { value: 'PRECIO', label: 'Precio' },
  { value: 'SIN_RESPUESTA', label: 'Sin respuesta' },
  { value: 'COMPETENCIA', label: 'Competencia' },
  { value: 'PROYECTO_CANCELADO', label: 'Proyecto cancelado' },
  { value: 'OTRO', label: 'Otro' },
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
