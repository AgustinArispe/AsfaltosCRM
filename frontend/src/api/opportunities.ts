import { PIPELINE_STAGES } from '../pipeline/config'
import type {
  LossReason,
  OpportunityDetail,
  OpportunityNote,
  OpportunityNotePage,
  OpportunitySummary,
  PaginatedResponse,
  PipelineStatus,
  QuoteProductInput,
} from '../pipeline/types'
import { apiRequest } from './client'

export type ApiSession = {
  token: string
  onUnauthorized: () => void
  signal?: AbortSignal
}

const PIPELINE_PAGE_SIZE = 100

export async function listCustomerOpportunities(
  customerId: number,
  session: ApiSession,
): Promise<OpportunitySummary[]> {
  const items: OpportunitySummary[] = []
  let page = 1
  let total = 0

  do {
    const query = new URLSearchParams({
      customer_id: String(customerId),
      page: String(page),
      page_size: String(PIPELINE_PAGE_SIZE),
    })
    const response = await apiRequest<PaginatedResponse<OpportunitySummary>>(
      `/opportunities?${query}`,
      session,
    )
    items.push(...response.items)
    total = response.total
    page += 1

    if (response.items.length === 0) break
  } while (items.length < total)

  return items
}

export function getOpportunityDetail(opportunityId: number, session: ApiSession) {
  return apiRequest<OpportunityDetail>(`/opportunities/${opportunityId}`, session)
}

async function listOpportunityStage(
  stage: PipelineStatus,
  session: ApiSession,
): Promise<OpportunitySummary[]> {
  const items: OpportunitySummary[] = []
  let page = 1
  let total = 0

  do {
    const query = new URLSearchParams({
      status: stage,
      page: String(page),
      page_size: String(PIPELINE_PAGE_SIZE),
    })
    const response = await apiRequest<PaginatedResponse<OpportunitySummary>>(
      `/opportunities?${query}`,
      session,
    )
    items.push(...response.items)
    total = response.total
    page += 1

    if (response.items.length === 0) break
  } while (items.length < total)

  return items
}

export async function listPipelineOpportunities(
  session: ApiSession,
): Promise<OpportunitySummary[]> {
  const opportunitiesByStage = await Promise.all(
    PIPELINE_STAGES.map((stage) => listOpportunityStage(stage.status, session)),
  )
  return opportunitiesByStage.flat()
}

export function quoteOpportunity(
  opportunityId: number,
  products: QuoteProductInput[],
  session: ApiSession,
) {
  return apiRequest<OpportunitySummary>(`/opportunities/${opportunityId}/quote`, {
    ...session,
    method: 'POST',
    body: { products },
  })
}

export function updateOpportunityQuoteProducts(
  opportunityId: number,
  products: QuoteProductInput[],
  expectedUpdatedAt: string,
  session: ApiSession,
) {
  return apiRequest<OpportunityDetail>(`/opportunities/${opportunityId}/quote-products`, {
    ...session,
    method: 'PUT',
    body: { products, expected_updated_at: expectedUpdatedAt },
  })
}

export function updateOpportunityAssignee(
  opportunityId: number,
  assignedUserId: number | null,
  expectedUpdatedAt: string,
  session: ApiSession,
) {
  return apiRequest<OpportunityDetail>(`/opportunities/${opportunityId}/assignee`, {
    ...session,
    method: 'PUT',
    body: { assigned_user_id: assignedUserId, expected_updated_at: expectedUpdatedAt },
  })
}

export function moveOpportunityToNegotiation(opportunityId: number, session: ApiSession) {
  return apiRequest<OpportunitySummary>(`/opportunities/${opportunityId}/move-to-negotiation`, {
    ...session,
    method: 'POST',
    body: {},
  })
}

export function winOpportunity(opportunityId: number, session: ApiSession) {
  return apiRequest<OpportunitySummary>(`/opportunities/${opportunityId}/win`, {
    ...session,
    method: 'POST',
    body: {},
  })
}

export function loseOpportunity(
  opportunityId: number,
  lossReason: LossReason,
  session: ApiSession,
) {
  return apiRequest<OpportunitySummary>(`/opportunities/${opportunityId}/lose`, {
    ...session,
    method: 'POST',
    body: { loss_reason: lossReason },
  })
}

export function reopenOpportunity(opportunityId: number, session: ApiSession) {
  return apiRequest<OpportunityDetail>(`/opportunities/${opportunityId}/reopen`, {
    ...session,
    method: 'POST',
    body: { command_id: crypto.randomUUID(), expected_status: 'PERDIDA' },
  })
}

export function listOpportunityNotes(opportunityId: number, session: ApiSession) {
  return apiRequest<OpportunityNotePage>(`/opportunities/${opportunityId}/notes?limit=20`, session)
}

export function createOpportunityNote(
  opportunityId: number,
  body: string,
  session: ApiSession,
  clientGeneratedId?: string,
) {
  return apiRequest<OpportunityNote>(`/opportunities/${opportunityId}/notes`, {
    ...session,
    method: 'POST',
    body: { client_generated_id: clientGeneratedId ?? crypto.randomUUID(), body },
  })
}
