import { describe, expect, it } from 'vitest'
import { periodSelection, validDateRange } from './periods'

describe('Shared calendar periods', () => {
  it.each([
    ['2026-01-01T02:59:00Z', '2025-12-17', '2025-12-31'],
    ['2026-01-01T03:00:00Z', '2025-12-18', '2026-01-01'],
    ['2024-03-01T12:00:00Z', '2024-02-16', '2024-03-01'],
  ])('includes exactly 15 Buenos Aires calendar days at %s', (now, from, to) => {
    expect(periodSelection('last-15-days', new Date(now))).toEqual({
      preset: 'last-15-days',
      from,
      to,
    })
  })
  it('supports today, seven days, full months, year and unbounded history', () => {
    const now = new Date('2024-02-29T14:00:00Z')
    expect(periodSelection('today', now)).toMatchObject({ from: '2024-02-29', to: '2024-02-29' })
    expect(periodSelection('last-7-days', now)).toMatchObject({
      from: '2024-02-23',
      to: '2024-02-29',
    })
    expect(periodSelection('month', now)).toMatchObject({ from: '2024-02-01', to: '2024-02-29' })
    expect(periodSelection('three-months', now)).toMatchObject({
      from: '2023-12-01',
      to: '2024-02-29',
    })
    expect(periodSelection('year', now)).toMatchObject({ from: '2024-01-01', to: '2024-02-29' })
    expect(periodSelection('all', now)).toEqual({ preset: 'all', from: '', to: '' })
  })
  it('validates real dates, ordering and completeness before requests', () => {
    expect(validDateRange('2024-02-29', '2024-02-29')).toBe(true)
    expect(validDateRange('2026-02-29', '2026-03-01')).toBe(false)
    expect(validDateRange('2026-03-02', '2026-03-01')).toBe(false)
    expect(validDateRange('', '2026-03-01')).toBe(false)
  })
})
