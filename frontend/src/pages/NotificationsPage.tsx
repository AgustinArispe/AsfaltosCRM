import { useMemo, useRef, useState } from 'react'

import {
  deleteNotification,
  markAllActiveNotificationsAsRead,
  markNotificationAsRead,
  type NotificationView,
  type OperationalNotification,
  setNotificationReadState,
} from '../api/notifications'
import type { ApiSession } from '../api/opportunities'
import { useAuth } from '../auth/AuthContext'
import { useNotificationAttentionContext } from '../notifications/NotificationAttention'
import { useNotifications } from '../notifications/useNotifications'
import type { OpportunityStatus } from '../pipeline/types'
import { navigateRoute } from '../routing/router'
import { Button } from '../shared/Button'
import { ConfirmationDialog } from '../shared/ConfirmationDialog'
import { formatDateTime, formatTimeInStage } from '../shared/formatters'
import { Icon } from '../shared/Icon'
import { OverdueBadge } from '../shared/OverdueBadge'
import { SegmentedControl } from '../shared/SegmentedControl'
import { EmptyState, ErrorState, Skeleton } from '../shared/StatusStates'

const VIEW_SEGMENTS = [
  { value: 'all', label: 'Todas' },
  { value: 'active', label: 'Activas' },
  { value: 'unread', label: 'Sin leer' },
] as const
const READ_ERROR_STORAGE_KEY = 'faa-crm.notifications.read-error'

const STATUS_LABELS: Record<OpportunityStatus, string> = {
  NUEVA: 'Nueva',
  COTIZADA: 'Cotizada',
  NEGOCIACION: 'Negociación',
  GANADA: 'Ganada',
  PERDIDA: 'Pérdida',
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
  const concept = notification.type === 'NEW_LEAD' ? 'Nueva oportunidad recibida' : '¡Atrasado!'
  const evidence = [
    notification.read_at ? 'leída' : 'sin leer',
    notification.resolved_at ? 'resuelta' : 'activa',
  ].join(', ')
  return `${concept}: ${identityFor(notification)}. ${STATUS_LABELS[notification.opportunity.status]}. ${evidence}. ${formatTimeInStage(notification.created_at)}.`
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
  onDelete,
  onOpen,
  onToggleReadState,
}: {
  isPending: boolean
  notification: OperationalNotification
  onDelete: (notification: OperationalNotification) => void
  onOpen: (notification: OperationalNotification) => void
  onToggleReadState: (notification: OperationalNotification) => void
}) {
  const isUnread = notification.read_at === null
  const isResolved = notification.resolved_at !== null
  const statusLabel = STATUS_LABELS[notification.opportunity.status]
  const isNewLead = notification.type === 'NEW_LEAD'
  const toggleLabel = isUnread ? 'Marcar como leída' : 'Marcar como no leída'
  const deleteLabel = `Eliminar notificación: ${isNewLead ? 'Nueva oportunidad recibida' : '¡Atrasado!'} · ${identityFor(notification)}`
  return (
    <li className='notification-row-wrapper'>
      <button
        aria-label={rowName(notification)}
        aria-describedby={`notification-${notification.id}-details`}
        className={`notification-row ${isUnread ? 'notification-row--unread' : ''}`}
        disabled={isPending}
        onClick={() => onOpen(notification)}
        type='button'
      >
        <span className='notification-row__icon'>
          <Icon className='size-4' name={isNewLead ? 'bell' : 'clock'} />
        </span>
        <span className='notification-row__heading'>
          {isNewLead ? <strong>Nueva oportunidad recibida</strong> : <OverdueBadge />}
          {isUnread ? (
            <span className='notification-row__unread'>Sin leer</span>
          ) : (
            <span>Leída</span>
          )}
        </span>
        <span className='notification-row__identity'>{identityFor(notification)}</span>
        <span className='notification-row__status'>
          <strong>{statusLabel}</strong>
          <span>{isResolved ? 'Resuelta' : 'Activa'}</span>
        </span>
        <span className='notification-row__meta' id={`notification-${notification.id}-details`}>
          <time dateTime={notification.created_at} title={formatDateTime(notification.created_at)}>
            <span>{formatTimeInStage(notification.created_at)}</span>
            <small>{formatDateTime(notification.created_at)}</small>
          </time>
          {isPending ? <span>Guardando lectura…</span> : null}
        </span>
        <Icon className='notification-row__chevron' name='chevron-right' />
      </button>
      <button
        aria-label={`${toggleLabel}: ${identityFor(notification)}`}
        className='notification-row__read-action'
        disabled={isPending}
        onClick={() => onToggleReadState(notification)}
        title={toggleLabel}
        type='button'
      >
        <Icon className='size-4' name={isUnread ? 'check' : 'inbox'} />
      </button>
      <button
        aria-label={deleteLabel}
        className='notification-row__delete-action'
        disabled={isPending}
        onClick={() => onDelete(notification)}
        title='Eliminar notificación'
        type='button'
      >
        <Icon className='size-4' name='trash' />
      </button>
    </li>
  )
}

export function NotificationsPage() {
  const { token, logout } = useAuth()
  const [view, setView] = useState<NotificationView>(() =>
    new URLSearchParams(window.location.search).get('view') === 'active' ? 'active' : 'all',
  )
  const [pendingIds, setPendingIds] = useState<Set<number>>(new Set())
  const [isMarkingAll, setIsMarkingAll] = useState(false)
  const [notificationToDelete, setNotificationToDelete] = useState<OperationalNotification | null>(
    null,
  )
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
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
    removeNotification,
    refresh,
    removeActiveUnread,
    reconcileNotification,
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
          reconcileNotification(updated)
          if (notification.resolved_at === null) attention?.adjustCount(-1)
          attention?.refresh()
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
        surface: 'pipeline',
      },
      { origin: { kind: 'workspace', workspace: 'notifications' } },
    )
  }

  const toggleReadState = (notification: OperationalNotification) => {
    if (pendingIds.has(notification.id)) return
    const isRead = notification.read_at === null
    setPending(notification.id, true)
    setReadError(null)
    void setNotificationReadState(notification.id, isRead, session)
      .then((updated) => {
        reconcileNotification(updated)
        if (notification.resolved_at === null) attention?.adjustCount(isRead ? -1 : 1)
        attention?.refresh()
        setAnnouncement(
          isRead ? 'Notificación marcada como leída.' : 'Notificación marcada como no leída.',
        )
      })
      .catch(() =>
        setReadError(
          isRead
            ? 'No pudimos marcar la notificación como leída.'
            : 'No pudimos marcar la notificación como no leída.',
        ),
      )
      .finally(() => setPending(notification.id, false))
  }

  const markAllActiveAsRead = () => {
    if (isMarkingAll) return
    setIsMarkingAll(true)
    setReadError(null)
    void markAllActiveNotificationsAsRead(session)
      .then((response) => {
        if (view === 'unread') removeActiveUnread(response.updated_count)
        else refresh()
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

  const closeDeleteConfirmation = () => {
    if (isDeleting) return
    setNotificationToDelete(null)
    setDeleteError(null)
  }

  const confirmDelete = () => {
    const notification = notificationToDelete
    if (!notification || isDeleting) return
    setIsDeleting(true)
    setDeleteError(null)
    setPending(notification.id, true)
    void deleteNotification(notification.id, session)
      .then(() => {
        removeNotification(notification.id)
        if (notification.read_at === null && notification.resolved_at === null)
          attention?.adjustCount(-1)
        attention?.refresh()
        setNotificationToDelete(null)
        setAnnouncement('Notificación eliminada para todo el equipo.')
      })
      .catch(() => setDeleteError('No pudimos eliminar la notificación. Intentá nuevamente.'))
      .finally(() => {
        setIsDeleting(false)
        setPending(notification.id, false)
      })
  }

  return (
    <section aria-label='Historial de notificaciones' className='notifications-page'>
      <div className='notifications-page__controls'>
        <SegmentedControl
          label='Vista de notificaciones'
          onChange={(value) => {
            const next = value as NotificationView
            window.history.replaceState(
              window.history.state,
              '',
              next === 'all' ? '/notifications' : `/notifications?view=${next}`,
            )
            setView(next)
          }}
          segments={VIEW_SEGMENTS}
          value={view}
        />
        <div className='notifications-page__control-actions'>
          {isRefreshing ? (
            <span className='notifications-page__refreshing'>Actualizando…</span>
          ) : null}
          {hasLoadedUnreadActive ? (
            <Button isLoading={isMarkingAll} onClick={markAllActiveAsRead} size='compact'>
              Marcar activas como leídas
            </Button>
          ) : null}
        </div>
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
        <section className='workspace-empty-card notifications-empty-card'>
          <EmptyState
            description={
              view === 'unread'
                ? 'No hay notificaciones sin leer.'
                : view === 'active'
                  ? 'No hay seguimientos activos.'
                  : 'Las novedades comerciales aparecerán acá.'
            }
            title={
              view === 'unread'
                ? 'Sin notificaciones sin leer'
                : view === 'active'
                  ? 'Sin seguimientos activos'
                  : 'No tenés notificaciones por ahora'
            }
            icon='bell'
            size='small'
          />
        </section>
      ) : (
        <ol aria-label='Historial cronológico de notificaciones' className='notifications-list'>
          {items.map((notification) => (
            <NotificationRow
              isPending={pendingIds.has(notification.id)}
              key={notification.id}
              notification={notification}
              onDelete={(current) => {
                setDeleteError(null)
                setNotificationToDelete(current)
              }}
              onOpen={(current) => {
                lastActivatedRow.current = document.activeElement as HTMLButtonElement | null
                openNotification(current)
              }}
              onToggleReadState={toggleReadState}
            />
          ))}
        </ol>
      )}
      <ConfirmationDialog
        confirmLabel='Eliminar notificación'
        description='Esta acción afecta a todo el equipo.'
        error={deleteError}
        isOpen={notificationToDelete !== null}
        isPending={isDeleting}
        onCancel={closeDeleteConfirmation}
        onConfirm={confirmDelete}
        pendingLabel='Eliminando…'
        title='Eliminar notificación'
        variant='danger'
      >
        <p className='text-sm leading-6 text-[var(--text-secondary)]'>
          ¿Seguro que querés eliminar esta notificación? Dejará de estar disponible para todo el
          equipo.
        </p>
      </ConfirmationDialog>
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
