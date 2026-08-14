import type {
  HumanTemplateSendInput,
  WhatsAppConversationChangePage,
  WhatsAppConversationDetail,
  WhatsAppConversationPage,
  WhatsAppConversationSummary,
  WhatsAppHumanTemplate,
  WhatsAppMediaUpload,
  WhatsAppMessageChangePage,
  WhatsAppMessagePage,
  WhatsAppMessageType,
  WhatsAppOutboundResponse,
  WhatsAppSendIntent,
} from '../whatsapp/types'
import { apiBlobRequest, apiFormRequest, apiRequest } from './client'
import type { ApiSession } from './opportunities'

export type ConversationListRequest = {
  limit?: number
  pageCursor?: string | null
  waitingOnly: boolean
  unreadOnly: boolean
  search: string
}

export function listWhatsAppConversations(request: ConversationListRequest, session: ApiSession) {
  const query = new URLSearchParams({
    limit: String(request.limit ?? 50),
    waiting_only: String(request.waitingOnly),
    unread_only: String(request.unreadOnly),
  })
  if (request.pageCursor) query.set('page_cursor', request.pageCursor)
  const search = request.search.trim()
  if (search) query.set('search', search)
  return apiRequest<WhatsAppConversationPage>(`/whatsapp/conversations?${query}`, session)
}

export function listWhatsAppConversationChanges(cursor: string, session: ApiSession) {
  const query = new URLSearchParams({ cursor, limit: '500' })
  return apiRequest<WhatsAppConversationChangePage>(
    `/whatsapp/conversations/changes?${query}`,
    session,
  )
}

export function getWhatsAppConversation(conversationId: number, session: ApiSession) {
  return apiRequest<WhatsAppConversationDetail>(
    `/whatsapp/conversations/${conversationId}`,
    session,
  )
}

export function listWhatsAppHumanTemplates(conversationId: number, session: ApiSession) {
  return apiRequest<WhatsAppHumanTemplate[]>(
    `/whatsapp/conversations/${conversationId}/templates`,
    session,
  )
}

export function sendWhatsAppHumanTemplate(
  conversationId: number,
  input: HumanTemplateSendInput,
  clientGeneratedId: string,
  headerMediaRef: string | null,
  session: ApiSession,
) {
  return apiRequest<WhatsAppOutboundResponse>(
    `/whatsapp/conversations/${conversationId}/templates/send`,
    {
      ...session,
      method: 'POST',
      body: {
        template_name: input.template.name,
        language: input.template.language,
        parameters: input.parameters,
        ...(headerMediaRef ? { header_media_ref: headerMediaRef } : {}),
        client_generated_id: clientGeneratedId,
      },
    },
  )
}

export function listWhatsAppMessages(
  conversationId: number,
  beforeCursor: string | null,
  session: ApiSession,
) {
  const query = new URLSearchParams({ limit: '100' })
  if (beforeCursor) query.set('before_cursor', beforeCursor)
  return apiRequest<WhatsAppMessagePage>(
    `/whatsapp/conversations/${conversationId}/messages?${query}`,
    session,
  )
}

export function listWhatsAppMessageChanges(
  conversationId: number,
  cursor: string,
  session: ApiSession,
) {
  const query = new URLSearchParams({ cursor, limit: '500' })
  return apiRequest<WhatsAppMessageChangePage>(
    `/whatsapp/conversations/${conversationId}/messages/changes?${query}`,
    session,
  )
}

function outboundBody(intent: WhatsAppSendIntent): object {
  const retry = intent.retryOfMessageId ? { retry_of_message_id: intent.retryOfMessageId } : {}
  if (intent.messageType === 'TEXT') {
    return {
      message_type: 'TEXT',
      client_generated_id: intent.clientGeneratedId,
      body: intent.body ?? '',
      ...retry,
    }
  }
  return {
    message_type: intent.messageType,
    client_generated_id: intent.clientGeneratedId,
    media_ref: intent.mediaRef,
    ...(intent.body ? { caption: intent.body } : {}),
    ...retry,
  }
}

export function sendWhatsAppMessage(
  conversationId: number,
  intent: WhatsAppSendIntent,
  session: ApiSession,
) {
  return apiRequest<WhatsAppOutboundResponse>(
    `/whatsapp/conversations/${conversationId}/messages`,
    { ...session, method: 'POST', body: outboundBody(intent) },
  )
}

export function markWhatsAppConversationRead(conversationId: number, session: ApiSession) {
  return apiRequest<WhatsAppConversationSummary>(`/whatsapp/conversations/${conversationId}/read`, {
    ...session,
    method: 'POST',
  })
}

export function linkWhatsAppOpportunity(
  conversationId: number,
  opportunityId: number,
  session: ApiSession,
) {
  return apiRequest<WhatsAppConversationDetail>(
    `/whatsapp/conversations/${conversationId}/opportunity-link`,
    { ...session, method: 'PUT', body: { opportunity_id: opportunityId } },
  )
}

export function unlinkWhatsAppOpportunity(conversationId: number, session: ApiSession) {
  return apiRequest<WhatsAppConversationDetail>(
    `/whatsapp/conversations/${conversationId}/opportunity-link`,
    { ...session, method: 'DELETE' },
  )
}

export function uploadWhatsAppMedia(
  file: File,
  messageType: Extract<WhatsAppMessageType, 'IMAGE' | 'DOCUMENT'>,
  session: ApiSession,
) {
  const formData = new FormData()
  formData.set('file', file)
  formData.set('metadata', JSON.stringify({ media_type: messageType }))
  return apiFormRequest<WhatsAppMediaUpload>('/whatsapp/media', formData, {
    ...session,
    method: 'POST',
  })
}

export function getWhatsAppMediaBlob(contentUrl: string, session: ApiSession) {
  return apiBlobRequest(contentUrl, session)
}
