import { type ButtonHTMLAttributes, forwardRef, type ReactNode } from 'react'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
type ButtonSize = 'compact' | 'default'

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:
    'border-[var(--action-primary)] bg-[var(--action-primary)] text-[var(--on-action-primary)] hover:border-[var(--action-primary-hover)] hover:bg-[var(--action-primary-hover)] active:border-[var(--action-primary-pressed)] active:bg-[var(--action-primary-pressed)]',
  secondary:
    'border-[var(--action-secondary)] bg-[var(--surface-raised)] text-[var(--action-secondary)] hover:bg-[var(--action-secondary-subtle)]',
  ghost:
    'border-transparent bg-transparent text-[var(--text-secondary)] hover:bg-[var(--hover)] hover:text-[var(--text-primary)]',
  danger:
    'border-[var(--destructive-solid)] bg-[var(--destructive-solid)] text-[var(--on-destructive)] hover:brightness-95',
}

const SIZE_CLASSES: Record<ButtonSize, string> = {
  compact: 'h-9 px-3 py-1.5 text-xs',
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
    'ui-pressable inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-[var(--radius-control)] border font-semibold leading-5 outline-none transition-[background-color,border-color,color,transform] duration-150 focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--focus-ring-offset)] disabled:cursor-not-allowed disabled:border-[var(--disabled-border)] disabled:bg-[var(--disabled-surface)] disabled:text-[var(--disabled-text)]',
    VARIANT_CLASSES[variant],
    SIZE_CLASSES[size],
    className,
  ].join(' ')
}

export const Button = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: ButtonVariant
    size?: ButtonSize
    isLoading?: boolean
  }
>(function Button(
  {
    variant = 'secondary',
    size = 'default',
    className,
    type = 'button',
    isLoading = false,
    children,
    disabled,
    ...props
  },
  ref,
) {
  return (
    <button
      aria-busy={isLoading || undefined}
      className={buttonClassName({ variant, size, className })}
      disabled={disabled || isLoading}
      ref={ref}
      type={type}
      {...props}
    >
      {isLoading ? <LoadingMark /> : null}
      {children}
    </button>
  )
})

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
