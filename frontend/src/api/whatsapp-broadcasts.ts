import type {
  Broadcast,
  BroadcastAttemptPage,
  BroadcastAuditPage,
  BroadcastConfirmationInput,
  BroadcastCreateInput,
  BroadcastPage,
  BroadcastProcessResult,
  BroadcastRecipientSelection,
  BroadcastRecipientsInput,
  BroadcastRecipientsPage,
  BroadcastTemplate,
  BroadcastUpdateInput,
  BroadcastValidation,
  RecipientStatus,
} from '../broadcasts/types'
import { apiRequest } from './client'
import type { ApiSession } from './opportunities'

export function listBroadcasts(session: ApiSession, cursor?: string) {
  const query = new URLSearchParams({ limit: '30' })
  if (cursor) query.set('cursor', cursor)
  return apiRequest<BroadcastPage>(`/whatsapp/broadcasts?${query}`, session)
}

export function getBroadcast(broadcastId: number, session: ApiSession) {
  return apiRequest<Broadcast>(`/whatsapp/broadcasts/${broadcastId}`, session)
}

export function listBroadcastTemplates(session: ApiSession) {
  return apiRequest<BroadcastTemplate[]>('/whatsapp/broadcast-templates', session)
}

export function createBroadcast(payload: BroadcastCreateInput, session: ApiSession) {
  return apiRequest<Broadcast>('/whatsapp/broadcasts', {
    ...session,
    method: 'POST',
    body: payload,
  })
}

export function updateBroadcast(
  broadcastId: number,
  payload: BroadcastUpdateInput,
  session: ApiSession,
) {
  return apiRequest<Broadcast>(`/whatsapp/broadcasts/${broadcastId}`, {
    ...session,
    method: 'PUT',
    body: payload,
  })
}

export function selectBroadcastRecipients(
  broadcastId: number,
  payload: BroadcastRecipientsInput,
  session: ApiSession,
) {
  return apiRequest<BroadcastRecipientSelection>(`/whatsapp/broadcasts/${broadcastId}/recipients`, {
    ...session,
    method: 'PUT',
    body: payload,
  })
}

export function validateBroadcast(
  broadcastId: number,
  expectedVersion: number,
  session: ApiSession,
) {
  return apiRequest<BroadcastValidation>(`/whatsapp/broadcasts/${broadcastId}/validate`, {
    ...session,
    method: 'POST',
    body: { expected_version: expectedVersion },
  })
}

export function confirmBroadcast(
  broadcastId: number,
  payload: BroadcastConfirmationInput,
  session: ApiSession,
) {
  return apiRequest<Broadcast>(`/whatsapp/broadcasts/${broadcastId}/confirm`, {
    ...session,
    method: 'POST',
    body: payload,
  })
}

export function startBroadcast(broadcastId: number, commandId: string, session: ApiSession) {
  return apiRequest<Broadcast>(`/whatsapp/broadcasts/${broadcastId}/start`, {
    ...session,
    method: 'POST',
    body: { command_id: commandId },
  })
}

export function processBroadcast(broadcastId: number, commandId: string, session: ApiSession) {
  return apiRequest<BroadcastProcessResult>(`/whatsapp/broadcasts/${broadcastId}/process`, {
    ...session,
    method: 'POST',
    body: { command_id: commandId },
  })
}

export function retryBroadcast(
  broadcastId: number,
  recipientId: number,
  commandId: string,
  session: ApiSession,
) {
  return apiRequest(`/whatsapp/broadcasts/${broadcastId}/retries`, {
    ...session,
    method: 'POST',
    body: { command_id: commandId, recipient_ids: [recipientId] },
  })
}

export function listBroadcastRecipients(
  broadcastId: number,
  session: ApiSession,
  options: { cursor?: string; status?: RecipientStatus; search?: string } = {},
) {
  const query = new URLSearchParams({ limit: '30' })
  if (options.cursor) query.set('cursor', options.cursor)
  if (options.status) query.set('status', options.status)
  if (options.search) query.set('search', options.search)
  return apiRequest<BroadcastRecipientsPage>(
    `/whatsapp/broadcasts/${broadcastId}/recipients?${query}`,
    session,
  )
}

export function listBroadcastAttempts(
  broadcastId: number,
  recipientId: number,
  session: ApiSession,
  cursor?: string,
) {
  const query = new URLSearchParams({ limit: '30' })
  if (cursor) query.set('cursor', cursor)
  return apiRequest<BroadcastAttemptPage>(
    `/whatsapp/broadcasts/${broadcastId}/recipients/${recipientId}/attempts?${query}`,
    session,
  )
}

export function listBroadcastAuditEvents(
  broadcastId: number,
  session: ApiSession,
  cursor?: string,
) {
  const query = new URLSearchParams({ limit: '30' })
  if (cursor) query.set('cursor', cursor)
  return apiRequest<BroadcastAuditPage>(
    `/whatsapp/broadcasts/${broadcastId}/audit-events?${query}`,
    session,
  )
}
