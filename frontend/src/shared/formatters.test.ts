import { describe, expect, it } from 'vitest'

import {
  formatDateTime,
  formatStageDuration,
  formatTimeInStage,
  sumQuantitiesKg,
} from './formatters'

describe('shared formatters', () => {
  it('formats timestamps in America/Argentina/Buenos_Aires', () => {
    expect(formatDateTime('2026-08-03T17:35:00Z')).toBe(
      '3 ago 2026, 14:35',
    )
  })

  it('formats concise stage durations', () => {
    const now = new Date('2026-08-20T12:00:00Z')

    expect(formatStageDuration('2026-08-20T08:00:00Z', now)).toBe('Hoy')
    expect(formatStageDuration('2026-08-19T12:00:00Z', now)).toBe('1 día')
    expect(formatStageDuration('2026-08-16T12:00:00Z', now)).toBe('4 días')
    expect(formatStageDuration('2026-08-06T12:00:00Z', now)).toBe('2 semanas')
    expect(formatTimeInStage('2026-08-06T12:00:00Z', now)).toBe(
      'Hace 2 semanas',
    )
  })

  it('adds quoted quantities represented as API decimals', () => {
    expect(sumQuantitiesKg(['2500.000', '1000.000'])).toBe(3500)
  })
})
