import type { OpportunityStatus } from './types'

export const OVERDUE_STAGE_DAYS = 7
export const OVERDUE_LABEL = '¡Atrasado!'

const OPEN_STATUSES: ReadonlySet<OpportunityStatus> = new Set(['NUEVA', 'COTIZADA', 'NEGOCIACION'])

export function isOpportunityOverdue(
  status: OpportunityStatus,
  currentStatusEnteredAt: string,
  now: number = Date.now(),
): boolean {
  if (!OPEN_STATUSES.has(status)) return false
  const enteredAt = Date.parse(currentStatusEnteredAt)
  if (!Number.isFinite(enteredAt) || enteredAt > now) return false
  return now - enteredAt >= OVERDUE_STAGE_DAYS * 86_400_000
}
