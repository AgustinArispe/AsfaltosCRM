import type { ButtonHTMLAttributes } from 'react'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
type ButtonSize = 'compact' | 'default'

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:
    'border-[var(--accent-solid)] bg-[var(--accent-solid)] text-[var(--on-accent)] hover:bg-[var(--accent-strong)]',
  secondary:
    'border-[var(--border-default)] bg-[var(--surface-raised)] text-[var(--text-primary)] hover:bg-[var(--surface-subtle)]',
  ghost:
    'border-transparent bg-transparent text-[var(--text-secondary)] hover:bg-[var(--hover)] hover:text-[var(--text-primary)]',
  danger:
    'border-[var(--destructive-solid)] bg-[var(--destructive-solid)] text-[var(--on-destructive)] hover:brightness-95',
}

const SIZE_CLASSES: Record<ButtonSize, string> = {
  compact: 'min-h-11 px-3 py-1.5 text-xs',
  default: 'min-h-11 px-3.5 py-2 text-sm',
}

export function buttonClassName({
  variant = 'secondary',
  size = 'default',
  className = '',
}: {
  variant?: ButtonVariant
  size?: ButtonSize
  className?: string
} = {}): string {
  return [
    'ui-pressable inline-flex items-center justify-center gap-2 rounded-[var(--radius-control)] border font-semibold leading-5 outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--focus-ring-offset)] disabled:cursor-not-allowed disabled:opacity-45',
    VARIANT_CLASSES[variant],
    SIZE_CLASSES[size],
    className,
  ].join(' ')
}

export function Button({
  variant = 'secondary',
  size = 'default',
  className,
  type = 'button',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant
  size?: ButtonSize
}) {
  return <button className={buttonClassName({ variant, size, className })} type={type} {...props} />
}
