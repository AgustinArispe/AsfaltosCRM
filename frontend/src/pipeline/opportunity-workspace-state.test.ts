import { describe, expect, it } from 'vitest'

import {
  EMPTY_OPPORTUNITY_WORKSPACE_STATE,
  opportunityWorkspaceReducer,
  workspaceOpportunities,
} from './opportunity-workspace-state'
import type { OpportunityDetail, OpportunitySummary } from './types'

function summary(id: number, status: OpportunitySummary['status']): OpportunitySummary {
  return {
    id,
    status,
    source: 'WEB',
    current_status_entered_at: '2026-09-07T12:00:00Z',
    customer: {
      id,
      name: `Cliente ${id}`,
      company: null,
      email: null,
      phone: null,
      province: null,
      legendary_historical_override: false,
    },
    assigned_user: null,
    products: [],
    created_at: '2026-09-01T12:00:00Z',
  }
}

function detail(id: number, status: OpportunityDetail['status']): OpportunityDetail {
  return {
    ...summary(id, status),
    history: [],
    loss_reason: status === 'PERDIDA' ? 'OTRO' : null,
    updated_at: '2026-09-07T12:00:00Z',
    web_intake: null,
  }
}

describe('opportunityWorkspaceReducer', () => {
  it('atomically caches authoritative detail and moves its board projection', () => {
    const initial = opportunityWorkspaceReducer(EMPTY_OPPORTUNITY_WORKSPACE_STATE, {
      type: 'replace-all',
      opportunities: [summary(1, 'NUEVA')],
    })
    const updated = opportunityWorkspaceReducer(initial, {
      type: 'cache-detail',
      opportunity: detail(1, 'COTIZADA'),
    })
    expect(updated.detailsById[1]?.status).toBe('COTIZADA')
    expect(updated.summariesById[1]?.status).toBe('COTIZADA')
  })

  it('removes lost cards while retaining their authoritative detail', () => {
    const updated = opportunityWorkspaceReducer(EMPTY_OPPORTUNITY_WORKSPACE_STATE, {
      type: 'cache-detail',
      opportunity: detail(2, 'PERDIDA'),
    })
    expect(workspaceOpportunities(updated)).toEqual([])
    expect(updated.detailsById[2]?.status).toBe('PERDIDA')
  })

  it('protects an entity changed after a board refresh started', () => {
    const current = opportunityWorkspaceReducer(EMPTY_OPPORTUNITY_WORKSPACE_STATE, {
      type: 'replace-all',
      opportunities: [summary(3, 'NEGOCIACION')],
    })
    const protectedState = opportunityWorkspaceReducer(current, {
      type: 'replace-stage',
      status: 'NEGOCIACION',
      opportunities: [summary(3, 'COTIZADA')],
      protectedOpportunityIds: [3],
    })
    expect(protectedState.summariesById[3]?.status).toBe('NEGOCIACION')
  })

  it('replaces unprotected stage contents and supports explicit removal and generations', () => {
    const current = opportunityWorkspaceReducer(EMPTY_OPPORTUNITY_WORKSPACE_STATE, {
      type: 'replace-all',
      opportunities: [summary(4, 'NUEVA')],
    })
    const replaced = opportunityWorkspaceReducer(current, {
      type: 'replace-stage',
      status: 'NUEVA',
      opportunities: [summary(5, 'NUEVA')],
    })
    const started = opportunityWorkspaceReducer(replaced, {
      type: 'start-mutation',
      opportunityId: 5,
    })
    const removed = opportunityWorkspaceReducer(started, { type: 'remove', opportunityId: 5 })
    expect(started.mutationGenerationById[5]).toBe(1)
    expect(workspaceOpportunities(removed)).toEqual([])
  })
})
