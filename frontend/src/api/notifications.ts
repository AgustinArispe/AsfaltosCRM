import type { OpportunityStatus, PaginatedResponse } from '../pipeline/types'
import { apiRequest } from './client'
import type { ApiSession } from './opportunities'

export const NOTIFICATION_PAGE_SIZE = 25

export type NotificationView = 'all' | 'unread'

export type OperationalNotification = {
  id: number
  type: 'OPPORTUNITY_STALE'
  created_at: string
  read_at: string | null
  resolved_at: string | null
  opportunity: {
    id: number
    status: OpportunityStatus
    current_status_entered_at: string
    customer: { id: number; name: string; company: string | null }
  }
}

export type NotificationReadAllResponse = { updated_count: number }

export function listNotifications(
  { page, view }: { page: number; view: NotificationView },
  session: ApiSession,
): Promise<PaginatedResponse<OperationalNotification>> {
  const query = new URLSearchParams({
    page: String(page),
    page_size: String(NOTIFICATION_PAGE_SIZE),
    include_resolved: 'true',
  })
  if (view === 'unread') query.set('unread_only', 'true')
  return apiRequest<PaginatedResponse<OperationalNotification>>(`/notifications?${query}`, session)
}

export function getNotificationTotal(
  unreadOnly: boolean,
  session: ApiSession,
): Promise<{ total: number }> {
  const query = new URLSearchParams({ page: '1', page_size: '1', unread_only: 'true' })
  if (!unreadOnly) query.delete('unread_only')
  return apiRequest<{ total: number }>(`/notifications?${query}`, session)
}

export function getActiveNotificationTotal(session: ApiSession): Promise<{ total: number }> {
  return getNotificationTotal(true, session)
}

export function markNotificationAsRead(
  notificationId: number,
  session: ApiSession,
): Promise<OperationalNotification> {
  return apiRequest<OperationalNotification>(`/notifications/${notificationId}/read`, {
    ...session,
    method: 'POST',
    body: {},
  })
}

export function markAllActiveNotificationsAsRead(
  session: ApiSession,
): Promise<NotificationReadAllResponse> {
  return apiRequest<NotificationReadAllResponse>('/notifications/read-all', {
    ...session,
    method: 'POST',
    body: {},
  })
}
