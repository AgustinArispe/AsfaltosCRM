import { describe, expect, it } from 'vitest'

import {
  formatDateTime,
  formatDecimalKg,
  formatDecimalRatioPercent,
  formatStageDuration,
  formatTimeInStage,
  sumQuantitiesKg,
} from './formatters'

describe('shared formatters', () => {
  it('formats timestamps in America/Argentina/Buenos_Aires', () => {
    expect(formatDateTime('2026-08-03T17:35:00Z')).toBe('3 ago 2026, 14:35')
  })

  it('formats concise stage durations', () => {
    const now = new Date('2026-08-20T12:00:00Z')

    expect(formatStageDuration('2026-08-20T08:00:00Z', now)).toBe('Hoy')
    expect(formatStageDuration('2026-08-19T12:00:00Z', now)).toBe('1 día')
    expect(formatStageDuration('2026-08-16T12:00:00Z', now)).toBe('4 días')
    expect(formatStageDuration('2026-08-06T12:00:00Z', now)).toBe('2 semanas')
    expect(formatTimeInStage('2026-08-06T12:00:00Z', now)).toBe('Hace 2 semanas')
  })

  it('adds quoted quantities represented as API decimals', () => {
    expect(sumQuantitiesKg(['2500.000', '1000.000'])).toBe(3500)
  })

  it('formats metric Decimals without recomputing them through floating-point arithmetic', () => {
    expect(formatDecimalKg('2500.125')).toBe('2.500,125 kg')
    expect(formatDecimalKg('10.000')).toBe('10 kg')
    expect(formatDecimalRatioPercent('0.6250')).toBe('62,5 %')
    expect(formatDecimalRatioPercent('1.0000')).toBe('100 %')
  })
})
