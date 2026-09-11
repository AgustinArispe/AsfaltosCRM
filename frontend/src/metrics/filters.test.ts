import { describe, expect, it } from 'vitest'

import {
  activeFilterCount,
  dashboardFiltersFromQuery,
  defaultDashboardFilters,
  filtersForCustomRange,
  filtersForPreset,
  sourceLabel,
  timelineGranularity,
} from './filters'

describe('Dashboard filters', () => {
  const now = new Date('2026-08-14T15:00:00Z')

  it('uses Buenos Aires monthly boundaries by default and serializes half-open ranges', () => {
    const filters = defaultDashboardFilters(now)

    expect(filters.from).toBe('2026-08-01T00:00:00-03:00')
    expect(filters.to).toBe('2026-09-01T00:00:00-03:00')
    expect(filters.customEnd).toBe('2026-08-31')
  })

  it('provides documented presets and keeps selected dimensions', () => {
    const initial = { ...defaultDashboardFilters(now), source: 'WEB' as const, productId: 3 }
    const threeMonths = filtersForPreset('last-three-months', initial, now)
    const year = filtersForPreset('year', initial, now)

    expect(threeMonths.from).toBe('2026-06-01T00:00:00-03:00')
    expect(threeMonths.to).toBe('2026-09-01T00:00:00-03:00')
    expect(threeMonths.source).toBe('WEB')
    expect(year.from).toBe('2026-01-01T00:00:00-03:00')
  })

  it('serializes inclusive custom end dates as the next Buenos Aires midnight', () => {
    const custom = filtersForCustomRange(defaultDashboardFilters(now), '2026-02-10', '2026-02-12')

    expect(custom.preset).toBe('custom')
    expect(custom.from).toBe('2026-02-10T00:00:00-03:00')
    expect(custom.to).toBe('2026-02-13T00:00:00-03:00')
  })

  it('restores a validated Dashboard range and dimensions from browser history', () => {
    const restored = dashboardFiltersFromQuery(
      '?period=three-months&from=2026-06-01&to=2026-08-31&source=WEB&product=3&province=Salta',
      now,
    )

    expect(restored.preset).toBe('last-three-months')
    expect(restored.from).toBe('2026-06-01T00:00:00-03:00')
    expect(restored.to).toBe('2026-09-01T00:00:00-03:00')
    expect(restored.source).toBe('WEB')
    expect(restored.productId).toBe(3)
    expect(restored.province).toBe('Salta')
  })

  it('uses daily Dashboard evolution through a full selected year', () => {
    const filters = defaultDashboardFilters(now)
    expect(timelineGranularity(filters)).toBe('day')
    expect(timelineGranularity(filtersForCustomRange(filters, '2026-08-01', '2026-08-10'))).toBe(
      'day',
    )
    expect(timelineGranularity(filtersForPreset('year', filters, now))).toBe('day')
    expect(timelineGranularity(filtersForCustomRange(filters, '2024-01-01', '2026-08-14'))).toBe(
      'month',
    )
    expect(
      activeFilterCount({ ...filters, source: 'WHATSAPP', productId: 1, province: 'Salta' }),
    ).toBe(3)
    expect(sourceLabel('WEB')).toBe('Web')
    expect(sourceLabel('WHATSAPP')).toBe('WhatsApp')
    expect(sourceLabel('REFERIDO')).toBe('Manual')
  })

  it('restores the REFERIDO origin from Dashboard URLs', () => {
    const restored = dashboardFiltersFromQuery(
      '?period=month&from=2026-09-01&to=2026-09-30&source=REFERIDO',
      new Date('2026-09-10T12:00:00-03:00'),
    )

    expect(restored.source).toBe('REFERIDO')
  })
})
