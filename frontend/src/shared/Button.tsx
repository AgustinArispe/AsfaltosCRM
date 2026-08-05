import type { ButtonHTMLAttributes } from 'react'

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
type ButtonSize = 'compact' | 'default'

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:
    'border-slate-800 bg-slate-800 text-white hover:border-slate-700 hover:bg-slate-700',
  secondary:
    'border-slate-300 bg-white text-slate-700 hover:border-slate-400 hover:bg-slate-50',
  ghost:
    'border-transparent bg-transparent text-slate-600 hover:bg-slate-100 hover:text-slate-900',
  danger:
    'border-red-700 bg-red-700 text-white hover:border-red-800 hover:bg-red-800',
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
    'ui-pressable inline-flex items-center justify-center gap-2 rounded-[4px] border font-semibold leading-5 outline-none focus-visible:ring-2 focus-visible:ring-slate-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-45',
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
  return (
    <button
      className={buttonClassName({ variant, size, className })}
      type={type}
      {...props}
    />
  )
}
