import type { UserRole } from '../auth/types'
import type { LeadSource, OpportunityStatus } from '../pipeline/types'

export type WhatsAppResolutionStatus = 'RESOLVED' | 'NEEDS_REVIEW'
export type WhatsAppDirection = 'INBOUND' | 'OUTBOUND'
export type WhatsAppMessageType = 'TEXT' | 'IMAGE' | 'DOCUMENT'
export type WhatsAppDispatchState =
  | 'PENDING'
  | 'IN_PROGRESS'
  | 'ACCEPTED'
  | 'DEFINITIVE_FAILED'
  | 'UNKNOWN'
export type WhatsAppProviderState =
  | 'RECEIVED'
  | 'SENT'
  | 'DELIVERED'
  | 'READ'
  | 'FAILED'
export type WhatsAppWindowReason = 'APPROVED_TEMPLATE_REQUIRED'
export type WhatsAppOpportunityLinkSource = 'AUTO_NEW_CONTACT' | 'MANUAL'

export type WhatsAppCustomerSummary = {
  id: number
  name: string
  company: string | null
  phone: string | null
  province: string | null
  is_available: boolean
}

export type WhatsAppUserSummary = {
  id: number
  full_name: string
  role: UserRole
}

export type WhatsAppOpportunitySummary = {
  id: number
  status: OpportunityStatus
  source: LeadSource
  created_at: string
  linked_at: string | null
  is_open: boolean
  is_available: boolean
}

export type WhatsAppOpportunityLink = {
  id: number
  opportunity: WhatsAppOpportunitySummary
  linked_at: string
  unlinked_at: string | null
  linked_by: WhatsAppUserSummary | null
  link_source: WhatsAppOpportunityLinkSource
  is_active: boolean
  is_actionable: boolean
}

export type WhatsAppConversationSummary = {
  id: number
  external_phone: string
  display_name: string | null
  resolution_status: WhatsAppResolutionStatus
  customer: WhatsAppCustomerSummary | null
  active_opportunity: WhatsAppOpportunitySummary | null
  opportunity_suggestions: WhatsAppOpportunitySummary[]
  last_message_at: string | null
  last_inbound_at: string | null
  last_outbound_at: string | null
  unread_count: number
  waiting_for_response: boolean
  waiting_since_at: string | null
  can_send_freeform: boolean
  window_expires_at: string | null
  template_required: boolean
  reason: WhatsAppWindowReason | null
  updated_at: string
  resource_updated_at: string
}

export type WhatsAppConversationDetail = WhatsAppConversationSummary & {
  opportunity_links: WhatsAppOpportunityLink[]
  created_at: string
}

export type WhatsAppConversationPage = {
  items: WhatsAppConversationSummary[]
  next_page_cursor: string | null
  sync_cursor: string
}

export type WhatsAppConversationChangePage = {
  items: WhatsAppConversationSummary[]
  next_cursor: string
  has_more: boolean
}

export type WhatsAppAttachment = {
  id: number
  media_type: WhatsAppMessageType
  mime_type: string | null
  filename: string | null
  size_bytes: number | null
  is_available: boolean
  content_url: string | null
}

export type WhatsAppMessageStatus = {
  dispatch_state: WhatsAppDispatchState | null
  provider_state: WhatsAppProviderState | null
  accepted_at: string | null
  sent_at: string | null
  delivered_at: string | null
  read_at: string | null
  failed_at: string | null
  error_code: string | null
  error_message: string | null
}

export type WhatsAppMessage = {
  id: number
  conversation_id: number
  external_message_id: string | null
  client_generated_id: string | null
  direction: WhatsAppDirection
  message_type: WhatsAppMessageType
  body: string | null
  sent_by: WhatsAppUserSummary | null
  retry_of_message_id: number | null
  is_retry: boolean
  message_at: string
  attachment: WhatsAppAttachment | null
  status: WhatsAppMessageStatus
  created_at: string
  updated_at: string
  resource_updated_at: string
}

export type WhatsAppMessagePage = {
  items: WhatsAppMessage[]
  next_before_cursor: string | null
  sync_cursor: string
}

export type WhatsAppMessageChangePage = {
  items: WhatsAppMessage[]
  next_cursor: string
  has_more: boolean
}

export type WhatsAppOutboundResponse = {
  message: WhatsAppMessage
  can_send_freeform: boolean
  window_expires_at: string | null
  template_required: boolean
  reason: WhatsAppWindowReason | null
}

export type WhatsAppMediaUpload = {
  media_ref: string
  media_type: 'IMAGE' | 'DOCUMENT'
  mime_type: string
  filename: string | null
  size_bytes: number
  content_url: string
}

export type WhatsAppFilters = {
  search: string
  waitingOnly: boolean
  unreadOnly: boolean
}

export type WhatsAppSendIntent = {
  clientGeneratedId: string
  messageType: WhatsAppMessageType
  body: string | null
  mediaRef: string | null
  retryOfMessageId: number | null
}

export type StagedWhatsAppAttachment = {
  file: File
  messageType: 'IMAGE' | 'DOCUMENT'
  previewUrl: string | null
}
