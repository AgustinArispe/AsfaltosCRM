export type OpportunityDetailRoute = {
  opportunityId: number
}

const OPPORTUNITY_DETAIL_PATTERN = /^\/opportunities\/([1-9]\d*)$/

export function matchOpportunityDetailRoute(
  pathname: string,
): OpportunityDetailRoute | null {
  const match = OPPORTUNITY_DETAIL_PATTERN.exec(pathname)
  if (!match) return null

  const opportunityId = Number(match[1])
  return Number.isSafeInteger(opportunityId) ? { opportunityId } : null
}
