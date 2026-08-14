import { useMemo, useRef, useState } from 'react'

import {
  markAllActiveNotificationsAsRead,
  markNotificationAsRead,
  type NotificationView,
  type OperationalNotification,
} from '../api/notifications'
import type { ApiSession } from '../api/opportunities'
import { useAuth } from '../auth/AuthContext'
import {
  refreshNotificationAttention,
  useNotificationAttentionContext,
} from '../notifications/NotificationAttention'
import { useNotifications } from '../notifications/useNotifications'
import type { OpportunityStatus } from '../pipeline/types'
import { navigateRoute } from '../routing/router'
import { Button } from '../shared/Button'
import { formatDateTime, formatTimeInStage } from '../shared/formatters'
import { SegmentedControl } from '../shared/SegmentedControl'
import { EmptyState, ErrorState, Skeleton } from '../shared/StatusStates'

const VIEW_SEGMENTS = [
  { value: 'all', label: 'Todas' },
  { value: 'unread', label: 'Sin leer' },
] as const
const READ_ERROR_STORAGE_KEY = 'faa-crm.notifications.read-error'

const STATUS_LABELS: Record<OpportunityStatus, string> = {
  NUEVA: 'Nueva',
  COTIZADA: 'Cotizada',
  NEGOCIACION: 'Negociación',
  GANADA: 'Ganada',
  PERDIDA: 'Perdida',
}

function identityFor(notification: OperationalNotification): string {
  const name = notification.opportunity.customer.name.trim()
  const company = notification.opportunity.customer.company?.trim() ?? ''
  if (!name && !company) return 'Cliente sin identificar'
  if (!company || company.localeCompare(name, 'es', { sensitivity: 'accent' }) === 0)
    return name || company
  return `${name || 'Cliente sin identificar'} · ${company}`
}

function rowName(notification: OperationalNotification): string {
  const evidence = [
    notification.read_at ? 'leída' : 'sin leer',
    notification.resolved_at ? 'resuelta' : 'activa',
  ].join(', ')
  return `Seguimiento pendiente: ${identityFor(notification)}. ${STATUS_LABELS[notification.opportunity.status]}. ${evidence}. ${formatTimeInStage(notification.created_at)}.`
}

function NotificationSkeleton() {
  return (
    <div aria-label='Cargando notificaciones' className='notifications-list' role='status'>
      {[1, 2, 3, 4].map((item) => (
        <div className='notification-row notification-row--skeleton' key={item}>
          <Skeleton className='h-4 w-36' />
          <Skeleton className='mt-2 h-3 w-3/5' />
          <Skeleton className='mt-4 h-3 w-28' />
        </div>
      ))}
    </div>
  )
}

function NotificationRow({
  isPending,
  notification,
  onOpen,
}: {
  isPending: boolean
  notification: OperationalNotification
  onOpen: (notification: OperationalNotification) => void
}) {
  const isUnread = notification.read_at === null
  const isResolved = notification.resolved_at !== null
  const statusLabel = STATUS_LABELS[notification.opportunity.status]
  return (
    <li>
      <button
        aria-label={rowName(notification)}
        aria-describedby={`notification-${notification.id}-details`}
        className={`notification-row ${isUnread ? 'notification-row--unread' : ''}`}
        disabled={isPending}
        onClick={() => onOpen(notification)}
        type='button'
      >
        <span className='notification-row__heading'>
          <strong>Seguimiento pendiente</strong>
          {isUnread ? (
            <span className='notification-row__unread'>Sin leer</span>
          ) : (
            <span>Leída</span>
          )}
        </span>
        <span className='notification-row__identity'>{identityFor(notification)}</span>
        <span className='notification-row__description'>
          La oportunidad sigue sin cambio de etapa.
        </span>
        <span className='notification-row__meta' id={`notification-${notification.id}-details`}>
          <time dateTime={notification.created_at} title={formatDateTime(notification.created_at)}>
            {formatTimeInStage(notification.created_at)}
          </time>
          <span>Estado: {statusLabel}</span>
          {isResolved ? <span>Resuelta</span> : <span>Activa</span>}
          {isPending ? <span>Guardando lectura…</span> : null}
        </span>
      </button>
    </li>
  )
}

export function NotificationsPage() {
  const { token, logout } = useAuth()
  const [view, setView] = useState<NotificationView>('all')
  const [pendingIds, setPendingIds] = useState<Set<number>>(new Set())
  const [isMarkingAll, setIsMarkingAll] = useState(false)
  const [readError, setReadError] = useState<string | null>(() => {
    const saved = window.sessionStorage.getItem(READ_ERROR_STORAGE_KEY)
    window.sessionStorage.removeItem(READ_ERROR_STORAGE_KEY)
    return saved
  })
  const [announcement, setAnnouncement] = useState('')
  const lastActivatedRow = useRef<HTMLButtonElement | null>(null)
  const session = useMemo<ApiSession>(
    () => ({ token: token ?? '', onUnauthorized: logout }),
    [logout, token],
  )
  const attention = useNotificationAttentionContext()
  const {
    applyPendingFirstPage,
    error,
    hasLoaded,
    isLoadingMore,
    isRefreshing,
    items,
    loadMore,
    pendingFirstPage,
    refresh,
    replaceNotification,
    total,
  } = useNotifications(view, session)
  const hasLoadedUnreadActive = items.some(
    (notification) => notification.read_at === null && notification.resolved_at === null,
  )

  const setPending = (notificationId: number, isPending: boolean) => {
    setPendingIds((current) => {
      const next = new Set(current)
      if (isPending) next.add(notificationId)
      else next.delete(notificationId)
      return next
    })
  }

  const openNotification = (notification: OperationalNotification) => {
    if (pendingIds.has(notification.id)) return
    setReadError(null)
    if (notification.read_at === null) {
      setPending(notification.id, true)
      void markNotificationAsRead(notification.id, session)
        .then((updated) => {
          replaceNotification(updated)
          refreshNotificationAttention()
          setAnnouncement('Notificación marcada como leída.')
        })
        .catch(() => {
          const message = 'No pudimos guardar la lectura. La notificación sigue disponible.'
          window.sessionStorage.setItem(READ_ERROR_STORAGE_KEY, message)
          setReadError(message)
          lastActivatedRow.current?.focus()
        })
        .finally(() => setPending(notification.id, false))
    }
    navigateRoute(
      {
        kind: 'opportunity',
        opportunityId: notification.opportunity.id,
        surface: notification.opportunity.status === 'PERDIDA' ? 'lost' : 'pipeline',
      },
      { origin: { kind: 'workspace', workspace: 'notifications' } },
    )
  }

  const markAllActiveAsRead = () => {
    if (isMarkingAll) return
    setIsMarkingAll(true)
    setReadError(null)
    void markAllActiveNotificationsAsRead(session)
      .then((response) => {
        refresh()
        attention?.refresh()
        setAnnouncement(
          response.updated_count === 1
            ? 'Se marcó 1 notificación activa como leída.'
            : `Se marcaron ${response.updated_count} notificaciones activas como leídas.`,
        )
      })
      .catch(() => setReadError('No pudimos marcar las notificaciones activas como leídas.'))
      .finally(() => setIsMarkingAll(false))
  }

  return (
    <section aria-labelledby='notifications-workspace-title' className='notifications-page'>
      <header className='notifications-page__heading'>
        <div>
          <h2 id='notifications-workspace-title'>Notificaciones</h2>
          <p>Seguimientos comerciales. Marcar una lectura no elimina el historial.</p>
        </div>
        {hasLoadedUnreadActive ? (
          <Button disabled={isMarkingAll} onClick={markAllActiveAsRead} size='compact'>
            {isMarkingAll ? 'Marcando…' : 'Marcar activas como leídas'}
          </Button>
        ) : null}
      </header>
      <div className='notifications-page__controls'>
        <SegmentedControl
          label='Vista de notificaciones'
          onChange={(value) => setView(value as NotificationView)}
          segments={VIEW_SEGMENTS}
          value={view}
        />
        {isRefreshing ? (
          <span className='notifications-page__refreshing'>Actualizando…</span>
        ) : null}
      </div>
      {readError ? (
        <p className='notifications-page__feedback' role='alert'>
          {readError}
        </p>
      ) : null}
      {error === 'background' ? (
        <div className='notifications-page__stale' role='status'>
          <span>No pudimos actualizar. Conservamos el historial disponible.</span>
          <button onClick={refresh} type='button'>
            Reintentar
          </button>
        </div>
      ) : null}
      {pendingFirstPage ? (
        <button
          className='notifications-page__new-items'
          onClick={applyPendingFirstPage}
          type='button'
        >
          Nuevas notificaciones disponibles
        </button>
      ) : null}
      {!hasLoaded && !error ? (
        <NotificationSkeleton />
      ) : error === 'initial' ? (
        <ErrorState message='No pudimos cargar las notificaciones.' onRetry={refresh} />
      ) : items.length === 0 ? (
        <EmptyState
          description={
            view === 'unread'
              ? 'No hay notificaciones sin leer.'
              : 'Todavía no hay historial de notificaciones.'
          }
          title={
            view === 'unread' ? 'Sin notificaciones sin leer' : 'Sin historial de notificaciones'
          }
        />
      ) : (
        <ol aria-label='Historial cronológico de notificaciones' className='notifications-list'>
          {items.map((notification) => (
            <NotificationRow
              isPending={pendingIds.has(notification.id)}
              key={notification.id}
              notification={notification}
              onOpen={(current) => {
                lastActivatedRow.current = document.activeElement as HTMLButtonElement | null
                openNotification(current)
              }}
            />
          ))}
        </ol>
      )}
      {items.length < total ? (
        <div className='notifications-page__load-more'>
          <Button disabled={isLoadingMore} onClick={loadMore} size='compact'>
            {isLoadingMore ? 'Cargando…' : 'Cargar más'}
          </Button>
        </div>
      ) : null}
      <p aria-atomic='true' aria-live='polite' className='sr-only'>
        {announcement}
      </p>
    </section>
  )
}
