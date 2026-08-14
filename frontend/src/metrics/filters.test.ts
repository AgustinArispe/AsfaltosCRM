import { describe, expect, it } from 'vitest'

import {
  activeFilterCount,
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

  it('chooses day only up to the backend bucket limit and exposes compact filter evidence', () => {
    const filters = defaultDashboardFilters(now)
    expect(timelineGranularity(filters)).toBe('day')
    expect(timelineGranularity(filtersForPreset('year', filters, now))).toBe('day')
    expect(timelineGranularity(filtersForCustomRange(filters, '2024-01-01', '2026-08-14'))).toBe(
      'month',
    )
    expect(
      activeFilterCount({ ...filters, source: 'WHATSAPP', productId: 1, province: 'Salta' }),
    ).toBe(3)
    expect(sourceLabel('WEB')).toBe('Web')
    expect(sourceLabel('WHATSAPP')).toBe('WhatsApp')
  })
})
