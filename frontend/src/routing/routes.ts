export type OpportunityDetailRoute = {
  opportunityId: number
}

export type CustomerDetailRoute = {
  customerId: number
}

const OPPORTUNITY_DETAIL_PATTERN = /^\/opportunities\/([1-9]\d*)$/
const CUSTOMER_DETAIL_PATTERN = /^\/customers\/([1-9]\d*)$/

export function matchOpportunityDetailRoute(pathname: string): OpportunityDetailRoute | null {
  const match = OPPORTUNITY_DETAIL_PATTERN.exec(pathname)
  if (!match) return null

  const opportunityId = Number(match[1])
  return Number.isSafeInteger(opportunityId) ? { opportunityId } : null
}

export function matchCustomerDetailRoute(pathname: string): CustomerDetailRoute | null {
  const match = CUSTOMER_DETAIL_PATTERN.exec(pathname)
  if (!match) return null

  const customerId = Number(match[1])
  return Number.isSafeInteger(customerId) ? { customerId } : null
}
