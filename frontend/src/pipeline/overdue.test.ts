import { describe, expect, it } from 'vitest'

import { isOpportunityOverdue } from './overdue'

const NOW = Date.parse('2026-09-16T12:00:00Z')

describe('isOpportunityOverdue', () => {
  it('marks every open stage overdue at the exact seven-day boundary', () => {
    for (const status of ['NUEVA', 'COTIZADA', 'NEGOCIACION'] as const) {
      expect(isOpportunityOverdue(status, '2026-09-09T12:00:00Z', NOW)).toBe(true)
    }
  })

  it('excludes newer, terminal, invalid, and future stage entries', () => {
    expect(isOpportunityOverdue('NUEVA', '2026-09-09T12:00:01Z', NOW)).toBe(false)
    expect(isOpportunityOverdue('GANADA', '2026-08-01T12:00:00Z', NOW)).toBe(false)
    expect(isOpportunityOverdue('PERDIDA', '2026-08-01T12:00:00Z', NOW)).toBe(false)
    expect(isOpportunityOverdue('NUEVA', 'fecha-invalida', NOW)).toBe(false)
    expect(isOpportunityOverdue('NUEVA', '2026-09-17T12:00:00Z', NOW)).toBe(false)
  })
})
