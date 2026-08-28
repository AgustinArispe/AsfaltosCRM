import type { ReactNode } from 'react'

export type BadgeTone =
  | 'neutral'
  | 'new'
  | 'quoted'
  | 'negotiation'
  | 'won'
  | 'lost'
  | 'unknown'
  | 'legendary'
  | 'active'

const TONE_CLASSES: Record<BadgeTone, string> = {
  neutral: 'border-[var(--border-default)] bg-[var(--surface-subtle)] text-[var(--text-secondary)]',
  new: 'border-[var(--action-secondary)] bg-[var(--action-secondary-subtle)] text-[var(--selection-text)]',
  quoted: 'border-[var(--accent-strong)] bg-[var(--accent-subtle)] text-[var(--text-primary)]',
  negotiation:
    'border-[var(--warning-border)] bg-[var(--warning-subtle)] text-[var(--warning-text)]',
  won: 'border-[var(--success-border)] bg-[var(--success-subtle)] text-[var(--success-text)]',
  lost: 'border-[var(--destructive-border)] bg-[var(--destructive-subtle)] text-[var(--destructive-text)]',
  unknown: 'border-[var(--uncertain)] bg-[var(--uncertain-muted)] text-[var(--uncertain)]',
  legendary:
    'border-[var(--legendary-border)] bg-[var(--legendary-subtle)] text-[var(--legendary-text)]',
  active: 'border-[var(--success-border)] bg-[var(--success-subtle)] text-[var(--success-text)]',
}

export function Badge({
  tone = 'neutral',
  children,
  className = '',
}: {
  tone?: BadgeTone
  children: ReactNode
  className?: string
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-semibold leading-5 ${TONE_CLASSES[tone]} ${className}`}
    >
      {children}
    </span>
  )
}

export const StatusPill = Badge
export const StatusBadge = Badge
