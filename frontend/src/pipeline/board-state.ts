import type { OpportunitySummary, PipelineStatus } from './types'

export type PipelineSort = 'newest' | 'oldest' | 'stage-oldest' | 'stage-newest'

export type PipelineFilters = {
  search: string
  source: OpportunitySummary['source'] | 'ALL'
  productId: string
  sort: PipelineSort
}

export const DEFAULT_PIPELINE_FILTERS: PipelineFilters = {
  search: '',
  source: 'ALL',
  productId: 'ALL',
  sort: 'newest',
}

export function customerIdentity(customer: OpportunitySummary['customer']): {
  primary: string
  supporting: string | null
} {
  const company = customer.company?.trim() ?? ''
  const name = customer.name?.trim() ?? ''
  if (company) return { primary: company, supporting: name && name !== company ? name : null }
  if (name) return { primary: name, supporting: null }
  return {
    primary: Number.isSafeInteger(customer.id)
      ? `Cliente #${customer.id}`
      : 'Cliente sin identificar',
    supporting: null,
  }
}

function normalized(value: string | null | undefined): string {
  return value?.trim().toLocaleLowerCase('es-AR') ?? ''
}

function compareBySort(sort: PipelineSort) {
  return (left: OpportunitySummary, right: OpportunitySummary): number => {
    if (sort === 'newest' || sort === 'oldest') {
      const createdDifference = Date.parse(left.created_at) - Date.parse(right.created_at)
      if (createdDifference !== 0) return sort === 'newest' ? -createdDifference : createdDifference
      return sort === 'newest' ? right.id - left.id : left.id - right.id
    }
    const stageDifference =
      Date.parse(left.current_status_entered_at) - Date.parse(right.current_status_entered_at)
    if (stageDifference !== 0) return sort === 'stage-oldest' ? stageDifference : -stageDifference
    return sort === 'stage-oldest' ? left.id - right.id : right.id - left.id
  }
}

export function projectPipeline(
  opportunities: OpportunitySummary[],
  filters: PipelineFilters,
): OpportunitySummary[] {
  const search = normalized(filters.search)
  return opportunities
    .filter((opportunity) => {
      if (filters.source !== 'ALL' && opportunity.source !== filters.source) return false
      if (
        filters.productId !== 'ALL' &&
        !opportunity.products.some((line) => String(line.product.id) === filters.productId)
      )
        return false
      if (!search) return true
      const identity = customerIdentity(opportunity.customer)
      return (
        normalized(identity.primary).includes(search) ||
        normalized(identity.supporting).includes(search)
      )
    })
    .sort(compareBySort(filters.sort))
}

export function opportunitiesForStage(
  opportunities: OpportunitySummary[],
  status: PipelineStatus,
): (OpportunitySummary & { status: PipelineStatus })[] {
  return opportunities.filter(
    (opportunity): opportunity is OpportunitySummary & { status: PipelineStatus } =>
      opportunity.status === status,
  )
}

export function activeFilterCount(filters: PipelineFilters, showStageAge: boolean): number {
  return (
    Number(Boolean(filters.search.trim())) +
    Number(filters.source !== 'ALL') +
    Number(filters.productId !== 'ALL') +
    Number(filters.sort !== 'newest') +
    Number(showStageAge)
  )
}
