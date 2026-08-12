import type { WhatsAppConversationSummary, WhatsAppFilters, WhatsAppMessage } from './types'

function timestamp(value: string | null): number {
  return value ? new Date(value).getTime() : Number.NEGATIVE_INFINITY
}

export function compareConversations(
  left: WhatsAppConversationSummary,
  right: WhatsAppConversationSummary,
): number {
  if (left.waiting_for_response !== right.waiting_for_response) {
    return left.waiting_for_response ? -1 : 1
  }
  if (left.unread_count !== right.unread_count) {
    return right.unread_count - left.unread_count
  }
  const activityDifference = timestamp(right.last_message_at) - timestamp(left.last_message_at)
  return activityDifference || right.id - left.id
}

function isAtLeastAsFresh(existing: string, incoming: string): boolean {
  return timestamp(incoming) >= timestamp(existing)
}

export function upsertConversations(
  existing: readonly WhatsAppConversationSummary[],
  incoming: readonly WhatsAppConversationSummary[],
): WhatsAppConversationSummary[] {
  const byId = new Map(existing.map((conversation) => [conversation.id, conversation]))
  for (const conversation of incoming) {
    const previous = byId.get(conversation.id)
    if (
      !previous ||
      isAtLeastAsFresh(previous.resource_updated_at, conversation.resource_updated_at)
    ) {
      byId.set(conversation.id, conversation)
    }
  }
  return [...byId.values()].sort(compareConversations)
}

function normalizedSearchValue(value: string): string {
  return value.trim().toLocaleLowerCase('es-AR')
}

function phoneDigits(value: string): string {
  return value.replace(/\D/g, '')
}

export function conversationMatchesFilters(
  conversation: WhatsAppConversationSummary,
  filters: WhatsAppFilters,
): boolean {
  if (filters.waitingOnly && !conversation.waiting_for_response) return false
  if (filters.unreadOnly && conversation.unread_count === 0) return false

  const search = normalizedSearchValue(filters.search)
  if (!search) return true
  const customer = conversation.customer
  const textValues = [
    conversation.display_name,
    conversation.external_phone,
    customer?.name,
    customer?.company,
  ]
  if (textValues.some((value) => (value ? normalizedSearchValue(value).includes(search) : false))) {
    return true
  }
  const searchedDigits = phoneDigits(search)
  return (
    searchedDigits.length > 0 && phoneDigits(conversation.external_phone).includes(searchedDigits)
  )
}

export function filterConversations(
  conversations: readonly WhatsAppConversationSummary[],
  filters: WhatsAppFilters,
): WhatsAppConversationSummary[] {
  return conversations.filter((conversation) => conversationMatchesFilters(conversation, filters))
}

export function upsertMessages(
  existing: readonly WhatsAppMessage[],
  incoming: readonly WhatsAppMessage[],
): WhatsAppMessage[] {
  const byId = new Map(existing.map((message) => [message.id, message]))
  for (const message of incoming) {
    const previous = byId.get(message.id)
    if (!previous || isAtLeastAsFresh(previous.resource_updated_at, message.resource_updated_at)) {
      byId.set(message.id, message)
    }
  }
  return [...byId.values()].sort((left, right) => {
    const timeDifference = timestamp(left.message_at) - timestamp(right.message_at)
    return timeDifference || left.id - right.id
  })
}

export function conversationDisplayName(conversation: WhatsAppConversationSummary): string {
  return conversation.customer?.name || conversation.display_name || conversation.external_phone
}

export function conversationActivityLabel(conversation: WhatsAppConversationSummary): string {
  if (conversation.resolution_status === 'NEEDS_REVIEW') {
    return 'Identidad pendiente de revisión'
  }
  if (conversation.waiting_for_response) return 'Cliente espera respuesta'
  if (
    conversation.last_message_at &&
    conversation.last_outbound_at === conversation.last_message_at
  ) {
    return 'Respondida por el equipo'
  }
  return conversation.last_message_at ? 'Conversación atendida' : 'Sin mensajes'
}
