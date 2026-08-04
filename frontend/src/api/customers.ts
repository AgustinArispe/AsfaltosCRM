import { apiRequest } from './client'
import type { ApiSession } from './opportunities'
import type {
  CustomerDetail,
  CustomerSummary,
  CustomerUpdatePayload,
  CustomerWritePayload,
} from '../customers/types'
import type { PaginatedResponse } from '../pipeline/types'

export type CustomerListParams = {
  page: number
  pageSize: number
  search?: string
}

export function listCustomers(
  { page, pageSize, search }: CustomerListParams,
  session: ApiSession,
) {
  const query = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })
  if (search) query.set('search', search)

  return apiRequest<PaginatedResponse<CustomerSummary>>(
    `/customers?${query}`,
    session,
  )
}

export function getCustomer(customerId: number, session: ApiSession) {
  return apiRequest<CustomerDetail>(`/customers/${customerId}`, session)
}

export function createCustomer(
  payload: CustomerWritePayload,
  session: ApiSession,
) {
  return apiRequest<CustomerSummary>('/customers', {
    ...session,
    method: 'POST',
    body: payload,
  })
}

export function updateCustomer(
  customerId: number,
  payload: CustomerUpdatePayload,
  session: ApiSession,
) {
  return apiRequest<CustomerSummary>(`/customers/${customerId}`, {
    ...session,
    method: 'PATCH',
    body: payload,
  })
}

export function deleteCustomer(customerId: number, session: ApiSession) {
  return apiRequest<null>(`/customers/${customerId}`, {
    ...session,
    method: 'DELETE',
  })
}
