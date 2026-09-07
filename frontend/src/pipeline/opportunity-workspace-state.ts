import type { OpportunityDetail, OpportunitySummary, PipelineStatus } from './types'

export type OpportunityWorkspaceState = {
  summariesById: Record<number, OpportunitySummary>
  detailsById: Record<number, OpportunityDetail>
  mutationGenerationById: Record<number, number>
}

export type OpportunityWorkspaceAction =
  | { type: 'replace-all'; opportunities: OpportunitySummary[] }
  | {
      type: 'replace-stage'
      status: PipelineStatus
      opportunities: OpportunitySummary[]
      protectedOpportunityIds?: number[]
    }
  | { type: 'upsert'; opportunity: OpportunitySummary | OpportunityDetail }
  | { type: 'cache-detail'; opportunity: OpportunityDetail }
  | { type: 'remove'; opportunityId: number }
  | { type: 'start-mutation'; opportunityId: number }

export const EMPTY_OPPORTUNITY_WORKSPACE_STATE: OpportunityWorkspaceState = {
  summariesById: {},
  detailsById: {},
  mutationGenerationById: {},
}

export function isOpportunityDetail(
  opportunity: OpportunitySummary | OpportunityDetail,
): opportunity is OpportunityDetail {
  return 'history' in opportunity && 'updated_at' in opportunity
}

export function opportunityWorkspaceReducer(
  state: OpportunityWorkspaceState,
  action: OpportunityWorkspaceAction,
): OpportunityWorkspaceState {
  if (action.type === 'replace-all') {
    return {
      ...state,
      summariesById: Object.fromEntries(
        action.opportunities.map((opportunity) => [opportunity.id, opportunity]),
      ),
    }
  }
  if (action.type === 'replace-stage') {
    const summariesById = { ...state.summariesById }
    const protectedIds = new Set(action.protectedOpportunityIds ?? [])
    for (const [id, opportunity] of Object.entries(summariesById)) {
      if (opportunity.status === action.status && !protectedIds.has(Number(id))) {
        delete summariesById[Number(id)]
      }
    }
    for (const opportunity of action.opportunities) {
      if (!protectedIds.has(opportunity.id)) summariesById[opportunity.id] = opportunity
    }
    return { ...state, summariesById }
  }
  if (action.type === 'remove') {
    const summariesById = { ...state.summariesById }
    delete summariesById[action.opportunityId]
    return { ...state, summariesById }
  }
  if (action.type === 'start-mutation') {
    return {
      ...state,
      mutationGenerationById: {
        ...state.mutationGenerationById,
        [action.opportunityId]: (state.mutationGenerationById[action.opportunityId] ?? 0) + 1,
      },
    }
  }
  const summariesById = { ...state.summariesById }
  if (action.opportunity.status === 'PERDIDA') delete summariesById[action.opportunity.id]
  else summariesById[action.opportunity.id] = action.opportunity
  const detail =
    action.type === 'cache-detail'
      ? action.opportunity
      : isOpportunityDetail(action.opportunity)
        ? action.opportunity
        : null
  if (detail) {
    return {
      ...state,
      summariesById,
      detailsById: { ...state.detailsById, [detail.id]: detail },
    }
  }
  return { ...state, summariesById }
}

export function workspaceOpportunities(state: OpportunityWorkspaceState): OpportunitySummary[] {
  return Object.values(state.summariesById)
}
