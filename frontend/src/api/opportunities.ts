import { apiRequest } from './client'
import { PIPELINE_STAGES } from '../pipeline/config'
import type {
  LossReason,
  OpportunitySummary,
  PaginatedResponse,
  PipelineStatus,
  QuoteProductInput,
} from '../pipeline/types'

export type ApiSession = {
  token: string
  onUnauthorized: () => void
  signal?: AbortSignal
}

const PIPELINE_PAGE_SIZE = 100

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
    PIPELINE_STAGES.map((stage) =>
      listOpportunityStage(stage.status, session),
    ),
  )
  return opportunitiesByStage.flat()
}

export function quoteOpportunity(
  opportunityId: number,
  products: QuoteProductInput[],
  session: ApiSession,
) {
  return apiRequest<OpportunitySummary>(
    `/opportunities/${opportunityId}/quote`,
    { ...session, method: 'POST', body: { products } },
  )
}

export function moveOpportunityToNegotiation(
  opportunityId: number,
  session: ApiSession,
) {
  return apiRequest<OpportunitySummary>(
    `/opportunities/${opportunityId}/move-to-negotiation`,
    { ...session, method: 'POST', body: {} },
  )
}

export function winOpportunity(
  opportunityId: number,
  session: ApiSession,
) {
  return apiRequest<OpportunitySummary>(
    `/opportunities/${opportunityId}/win`,
    { ...session, method: 'POST', body: {} },
  )
}

export function loseOpportunity(
  opportunityId: number,
  lossReason: LossReason,
  session: ApiSession,
) {
  return apiRequest<OpportunitySummary>(
    `/opportunities/${opportunityId}/lose`,
    { ...session, method: 'POST', body: { loss_reason: lossReason } },
  )
}
