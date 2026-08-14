export type BroadcastStatus = 'DRAFT' | 'CONFIRMED' | 'PROCESSING' | 'COMPLETED'
export type RecipientStatus =
  | 'DRAFT'
  | 'READY'
  | 'IN_PROGRESS'
  | 'ACCEPTED'
  | 'SENT'
  | 'DELIVERED'
  | 'READ'
  | 'FAILED'
  | 'UNKNOWN'
  | 'BLOCKED'

export type BroadcastTemplate = {
  external_id: string
  name: string
  language: string
  category: string
  status: string
  header_type: 'NONE' | 'IMAGE' | 'DOCUMENT'
  parameter_names: string[]
  header_media_required: boolean
}

export type BroadcastParameter = { name: string; value: string }

export type BroadcastOutcomes = {
  selected: number
  accepted: number
  sent: number
  delivered: number
  read: number
  failed: number
  unknown: number
  skipped: number
}

export type Broadcast = {
  id: number
  label: string
  status: BroadcastStatus
  version: number
  template_name: string
  template_language: string
  template_category: string
  template_header_type: 'TEXT' | 'IMAGE' | 'DOCUMENT' | null
  template_header_media_required: boolean
  header_media_ref: string | null
  parameters: BroadcastParameter[]
  recipient_count: number
  outcomes: BroadcastOutcomes | null
  validated_at: string | null
  confirmed_at: string | null
  started_at: string | null
  created_at: string
  updated_at: string
}

export type BroadcastPage = { items: Broadcast[]; next_cursor: string | null }
export type ValidationIssue = { category: string; count: number; recipient_ids: number[] }
export type BroadcastValidation = {
  broadcast_id: number
  version: number
  valid: boolean
  recipient_count: number
  validation_token: string | null
  expires_at: string | null
  issue_categories: ValidationIssue[]
  eligible_count: number
  excluded_count: number
}

export type BroadcastRecipient = {
  id: number
  customer_id: number
  customer_display_name: string
  phone_display: string
  status: RecipientStatus
  safe_reason: string | null
  retry_eligible: boolean
  conversation_id: number | null
  latest_attempt_at: string | null
  delivered_at: string | null
  read_at: string | null
  failed_at: string | null
}

export type BroadcastRecipientsPage = { items: BroadcastRecipient[]; next_cursor: string | null }
export type BroadcastProcessResult = {
  broadcast_id: number
  claimed_count: number
  completed_count: number
  remaining_count: number
  replayed: boolean
}

export type BroadcastAttempt = {
  id: number
  attempt_number: number
  occurred_at: string
  outcome: string
  safe_reason: string | null
}

export type BroadcastAttemptPage = { items: BroadcastAttempt[]; next_cursor: string | null }

export type BroadcastAuditEvent = {
  id: number
  event_type: string
  reason_code: string | null
  actor_user_id: number | null
  affected_count: number | null
  occurred_at: string
}

export type BroadcastAuditPage = { items: BroadcastAuditEvent[]; next_cursor: string | null }

export type BroadcastRecipientSelection = {
  broadcast_id: number
  version: number
  selected_count: number
  duplicate_customer_ids: number[]
  invalid_customer_ids: number[]
  missing_phone_customer_ids: number[]
  missing_consent_customer_ids: number[]
  replayed: boolean
}

export type BroadcastParameterInput = { name: string; value: string }

export type BroadcastCreateInput = {
  client_generated_id: string
  label: string
  template_external_id: string
  parameters: BroadcastParameterInput[]
  header_media_ref: string | null
}

export type BroadcastUpdateInput = Omit<BroadcastCreateInput, 'client_generated_id'> & {
  expected_version: number
}

export type BroadcastRecipientsInput = {
  command_id: string
  expected_version: number
  customer_ids: number[]
}

export type BroadcastConfirmationInput = {
  command_id: string
  expected_version: number
  validation_token: string
}
