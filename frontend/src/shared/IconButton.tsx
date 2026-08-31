import { type ButtonHTMLAttributes, forwardRef } from 'react'

import { buttonClassName } from './Button'
import { Icon, type IconName } from './Icon'

export const IconButton = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & {
    label: string
    icon: IconName
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
    size?: 'compact' | 'default'
  }
>(function IconButton(
  { label, icon, className, variant = 'ghost', size = 'default', ...props },
  ref,
) {
  return (
    <button
      aria-label={label}
      ref={ref}
      className={buttonClassName({
        variant,
        size,
        className: `${size === 'compact' ? 'size-9' : 'size-11'} px-0 ${className ?? ''}`,
      })}
      title={label}
      type='button'
      {...props}
    >
      <Icon name={icon} />
    </button>
  )
})
