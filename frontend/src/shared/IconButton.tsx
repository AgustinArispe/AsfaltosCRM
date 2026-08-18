import { type ButtonHTMLAttributes, forwardRef } from 'react'

import { buttonClassName } from './Button'
import { Icon, type IconName } from './Icon'

export const IconButton = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & {
    label: string
    icon: IconName
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  }
>(function IconButton({ label, icon, className, variant = 'ghost', ...props }, ref) {
  return (
    <button
      aria-label={label}
      ref={ref}
      className={buttonClassName({
        variant,
        size: 'compact',
        className: `size-11 px-0 ${className ?? ''}`,
      })}
      title={label}
      type='button'
      {...props}
    >
      <Icon name={icon} />
    </button>
  )
})
