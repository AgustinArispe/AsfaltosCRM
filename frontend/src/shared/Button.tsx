import type { ButtonHTMLAttributes, ReactNode } from 'react'

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
  isLoading = false,
  children,
  disabled,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant
  size?: ButtonSize
  isLoading?: boolean
}) {
  return (
    <button
      aria-busy={isLoading || undefined}
      className={buttonClassName({ variant, size, className })}
      disabled={disabled || isLoading}
      type={type}
      {...props}
    >
      {isLoading ? <LoadingMark /> : null}
      {children}
    </button>
  )
}

function LoadingMark(): ReactNode {
  return (
    <svg
      aria-hidden='true'
      className='size-4 animate-spin motion-reduce:animate-none'
      viewBox='0 0 20 20'
    >
      <circle
        className='opacity-25'
        cx='10'
        cy='10'
        fill='none'
        r='7'
        stroke='currentColor'
        strokeWidth='2'
      />
      <path d='M10 3a7 7 0 0 1 7 7' fill='none' stroke='currentColor' strokeWidth='2' />
    </svg>
  )
}
