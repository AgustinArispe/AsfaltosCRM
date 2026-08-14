import type { ReactNode } from 'react'

import { Button } from './Button'

export function Surface({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`ui-panel ${className}`}>{children}</section>
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <span aria-hidden='true' className={`ui-skeleton ${className}`} />
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <div className='ui-empty-state'>
      <h2>{title}</h2>
      <p>{description}</p>
      {action}
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className='ui-error-state' role='alert'>
      <p>{message}</p>
      {onRetry ? <Button onClick={onRetry}>Reintentar</Button> : null}
    </div>
  )
}

export function Avatar({ name, className = '' }: { name: string; className?: string }) {
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
  return (
    <span aria-label={name} className={`ui-avatar ${className}`} role='img'>
      {initials || '—'}
    </span>
  )
}

export function NotificationBadge({ count }: { count: number }) {
  if (count <= 0) return null
  const label = count > 99 ? '99 o más notificaciones sin leer' : `${count} notificaciones sin leer`
  return (
    <span aria-label={label} className='ui-notification-badge' role='status'>
      {count > 99 ? '99+' : count}
    </span>
  )
}

export function ChartSurface({
  title,
  children,
  showTitle = true,
}: {
  title: string
  children: ReactNode
  showTitle?: boolean
}) {
  return (
    <section aria-label={title} className='ui-chart-surface'>
      {showTitle ? <h2>{title}</h2> : null}
      {children}
    </section>
  )
}
