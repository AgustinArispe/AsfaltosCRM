import type {
  CustomerDetail,
  CustomerImportCommitResult,
  CustomerImportReport,
  CustomerNote,
  CustomerSummary,
  CustomerUpdatePayload,
  CustomerWritePayload,
} from '../customers/types'
import type { PaginatedResponse } from '../pipeline/types'
import { apiFormRequest, apiRequest } from './client'
import type { ApiSession } from './opportunities'

export type CustomerListParams = {
  page: number
  pageSize: number
  search?: string
}

export function listCustomers({ page, pageSize, search }: CustomerListParams, session: ApiSession) {
  const query = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })
  if (search) query.set('search', search)

  return apiRequest<PaginatedResponse<CustomerSummary>>(`/customers?${query}`, session)
}

export function getCustomer(customerId: number, session: ApiSession) {
  return apiRequest<CustomerDetail>(`/customers/${customerId}`, session)
}

export function createCustomer(payload: CustomerWritePayload, session: ApiSession) {
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

export function dryRunCustomerImport(file: File, clientImportId: string, session: ApiSession) {
  const formData = new FormData()
  formData.set('client_import_id', clientImportId)
  formData.set('file', file)
  return apiFormRequest<CustomerImportReport>('/customer-imports/dry-run', formData, {
    ...session,
    method: 'POST',
  })
}

export function getCustomerImport(batchId: number, session: ApiSession) {
  return apiRequest<CustomerImportReport>(`/customer-imports/${batchId}`, session)
}

export function commitCustomerImport(
  report: CustomerImportReport,
  commandId: string,
  session: ApiSession,
) {
  return apiRequest<CustomerImportCommitResult>(`/customer-imports/${report.id}/commit`, {
    ...session,
    method: 'POST',
    body: {
      command_id: commandId,
      expected_version: report.version,
      file_sha256: report.file_sha256,
    },
  })
}

export function listCustomerNotes(
  customerId: number,
  page: number,
  pageSize: number,
  session: ApiSession,
) {
  return apiRequest<PaginatedResponse<CustomerNote>>(
    `/customers/${customerId}/notes?page=${page}&page_size=${pageSize}`,
    session,
  )
}

export function createCustomerNote(
  customerId: number,
  body: string,
  commandId: string,
  session: ApiSession,
) {
  return apiRequest<CustomerNote>(`/customers/${customerId}/notes`, {
    ...session,
    method: 'POST',
    body: { body, command_id: commandId },
  })
}

export function updateCustomerNote(
  customerId: number,
  note: CustomerNote,
  body: string,
  pinned: boolean,
  session: ApiSession,
) {
  return apiRequest<CustomerNote>(`/customers/${customerId}/notes/${note.id}`, {
    ...session,
    method: 'PUT',
    body: { body, pinned, expected_updated_at: note.updated_at },
  })
}

export function archiveCustomerNote(customerId: number, noteId: number, session: ApiSession) {
  return apiRequest<null>(`/customers/${customerId}/notes/${noteId}`, {
    ...session,
    method: 'DELETE',
  })
}
