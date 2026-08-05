import type {
  LeadSource,
  LossReason,
  OpportunityStatus,
  PipelineStatus,
} from './types'
import type { BadgeTone } from '../shared/Badge'

export type PipelineStage = {
  status: PipelineStatus
  label: string
  singularLabel: string
  nextStatus: PipelineStatus | null
  accentClassName: string
  countClassName: string
  cardAccentClassName: string
}

export const PIPELINE_STAGES: readonly PipelineStage[] = [
  {
    status: 'NUEVA',
    label: 'Nuevos',
    singularLabel: 'Nueva',
    nextStatus: 'COTIZADA',
    accentClassName: 'border-t-slate-400',
    countClassName: 'border-slate-200 bg-slate-100 text-slate-700',
    cardAccentClassName: 'border-l-slate-400',
  },
  {
    status: 'COTIZADA',
    label: 'Cotizados',
    singularLabel: 'Cotizada',
    nextStatus: 'NEGOCIACION',
    accentClassName: 'border-t-blue-400',
    countClassName: 'border-blue-200 bg-blue-50 text-blue-800',
    cardAccentClassName: 'border-l-blue-400',
  },
  {
    status: 'NEGOCIACION',
    label: 'Negociación',
    singularLabel: 'Negociación',
    nextStatus: 'GANADA',
    accentClassName: 'border-t-amber-500',
    countClassName: 'border-amber-200 bg-amber-50 text-amber-900',
    cardAccentClassName: 'border-l-amber-500',
  },
  {
    status: 'GANADA',
    label: 'Ganados',
    singularLabel: 'Ganada',
    nextStatus: null,
    accentClassName: 'border-t-emerald-600',
    countClassName: 'border-emerald-200 bg-emerald-50 text-emerald-800',
    cardAccentClassName: 'border-l-emerald-600',
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

export function canMoveTo(
  from: PipelineStatus,
  to: PipelineStatus,
): boolean {
  return STAGE_BY_STATUS.get(from)?.nextStatus === to
}
