import { describe, expect, it } from 'vitest'

import { meaningfulPeakIndexes, timelineDayLabelInterval } from './DashboardVisuals'

describe('meaningfulPeakIndexes', () => {
  it('ignores zero-only and non-distinct maxima', () => {
    expect(meaningfulPeakIndexes([0, 0, 0])).toEqual([])
    expect(meaningfulPeakIndexes([3, 3, 3])).toEqual([])
  })

  it('highlights only one or two positive maxima', () => {
    expect(meaningfulPeakIndexes([1, 4, 2])).toEqual([1])
    expect(meaningfulPeakIndexes([4, 1, 4])).toEqual([0, 2])
  })
})

describe('timelineDayLabelInterval', () => {
  it('keeps every label for ranges up to 31 days', () => {
    expect(timelineDayLabelInterval(1)).toBe(1)
    expect(timelineDayLabelInterval(31)).toBe(1)
  })

  it('uses two-day and three-day intervals for medium ranges', () => {
    expect(timelineDayLabelInterval(32)).toBe(2)
    expect(timelineDayLabelInterval(60)).toBe(2)
    expect(timelineDayLabelInterval(61)).toBe(3)
    expect(timelineDayLabelInterval(100)).toBe(3)
  })

  it('caps longer ranges at approximately 31 visible labels', () => {
    expect(timelineDayLabelInterval(101)).toBe(4)
    expect(timelineDayLabelInterval(180)).toBe(6)
    expect(timelineDayLabelInterval(366)).toBe(12)
  })
})
