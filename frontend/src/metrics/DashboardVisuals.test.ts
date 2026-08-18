import { describe, expect, it } from 'vitest'

import { meaningfulPeakIndexes } from './DashboardVisuals'

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
