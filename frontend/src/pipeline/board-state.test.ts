import { describe, expect, it } from 'vitest'

import {
  activeFilterCount,
  customerIdentity,
  DEFAULT_PIPELINE_FILTERS,
  opportunitiesForStage,
  projectPipeline,
} from './board-state'
import type { OpportunitySummary } from './types'

function item(id: number, overrides: Partial<OpportunitySummary> = {}): OpportunitySummary {
  return {
    id,
    status: 'COTIZADA',
    source: id % 2 ? 'WEB' : 'WHATSAPP',
    current_status_entered_at: `2026-08-0${id}T12:00:00Z`,
    customer: {
      id: id + 10,
      name: `Nombre ${id}`,
      company: id === 3 ? null : `Empresa ${id}`,
      email: null,
      phone: null,
      province: null,
      legendary_historical_override: false,
    },
    assigned_user: null,
    products:
      id === 3
        ? []
        : [
            {
              product: { id: 7, name: 'Producto', is_active: true },
              quantity_kg: '1.000',
            },
          ],
    created_at: `2026-08-0${id}T10:00:00Z`,
    ...overrides,
  }
}

describe('board-state', () => {
  it('uses deterministic company, name, and malformed customer identity fallbacks', () => {
    expect(customerIdentity(item(1).customer)).toEqual({
      primary: 'Empresa 1',
      supporting: 'Nombre 1',
    })
    expect(customerIdentity(item(3).customer)).toEqual({ primary: 'Nombre 3', supporting: null })
    expect(
      customerIdentity({ ...item(1).customer, id: Number.NaN, name: ' ', company: ' ' }),
    ).toEqual({ primary: 'Cliente sin identificar', supporting: null })
    expect(customerIdentity({ ...item(1).customer, name: 'Empresa 1' })).toEqual({
      primary: 'Empresa 1',
      supporting: null,
    })
  })

  it('projects source, product and search locally with all documented stable orders', () => {
    const newest = item(3)
    const middle = item(2)
    const oldest = item(1, {
      created_at: '2026-08-01T10:00:00Z',
      current_status_entered_at: '2026-08-02T10:00:00Z',
    })
    const sameDateHigherId = item(4, {
      created_at: '2026-08-03T10:00:00Z',
      current_status_entered_at: newest.current_status_entered_at,
    })
    const items = [oldest, middle, newest, sameDateHigherId]
    expect(projectPipeline(items, DEFAULT_PIPELINE_FILTERS).map((value) => value.id)).toEqual([
      4, 3, 2, 1,
    ])
    expect(
      projectPipeline(items, { ...DEFAULT_PIPELINE_FILTERS, sort: 'oldest' }).map(
        (value) => value.id,
      ),
    ).toEqual([1, 2, 3, 4])
    expect(
      projectPipeline(items, { ...DEFAULT_PIPELINE_FILTERS, sort: 'stage-oldest' })[0]?.id,
    ).toBe(1)
    expect(
      projectPipeline(items, { ...DEFAULT_PIPELINE_FILTERS, sort: 'stage-newest' })[0]?.id,
    ).toBe(4)
    expect(
      projectPipeline(items, {
        ...DEFAULT_PIPELINE_FILTERS,
        source: 'WHATSAPP',
        productId: '7',
      }).map((value) => value.id),
    ).toEqual([4, 2])
    expect(
      projectPipeline(items, { ...DEFAULT_PIPELINE_FILTERS, search: 'nombre 3' }).map(
        (value) => value.id,
      ),
    ).toEqual([3])
  })

  it('counts active filters and confines a projection to its configured stage', () => {
    expect(activeFilterCount(DEFAULT_PIPELINE_FILTERS, false)).toBe(0)
    expect(
      activeFilterCount({ ...DEFAULT_PIPELINE_FILTERS, search: 'faa', sort: 'oldest' }, true),
    ).toBe(3)
    expect(
      opportunitiesForStage([item(1), item(2, { status: 'GANADA' })], 'GANADA').map(
        (value) => value.id,
      ),
    ).toEqual([2])
  })
})
