import { apiRequest } from './client'
import type { ApiSession } from './opportunities'

type NotificationPage = { total: number }

export function getActiveNotificationTotal(unreadOnly: boolean, session: ApiSession) {
  const query = new URLSearchParams({ page: '1', page_size: '1' })
  if (unreadOnly) query.set('unread_only', 'true')
  return apiRequest<NotificationPage>(`/notifications?${query}`, session)
}
