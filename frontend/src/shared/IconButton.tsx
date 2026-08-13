import type { ButtonHTMLAttributes } from 'react'

import { buttonClassName } from './Button'
import { Icon, type IconName } from './Icon'

export function IconButton({
  label,
  icon,
  className,
  variant = 'ghost',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  label: string
  icon: IconName
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
}) {
  return (
    <button
      aria-label={label}
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
}
