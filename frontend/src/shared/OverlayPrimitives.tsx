import { type ReactNode, useEffect, useRef, useState } from 'react'

export function Tooltip({ label, children }: { label: string; children: ReactNode }) {
  return (
    <span className='ui-tooltip' data-tooltip={label}>
      {children}
    </span>
  )
}

export function Popover({
  label,
  trigger,
  children,
}: {
  label: string
  trigger: ReactNode
  children: ReactNode
}) {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const closeOnPointerDown = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setIsOpen(false)
    }
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setIsOpen(false)
    }
    document.addEventListener('mousedown', closeOnPointerDown)
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('mousedown', closeOnPointerDown)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [])

  return (
    <div className='relative inline-block' ref={containerRef}>
      <button
        aria-expanded={isOpen}
        className='ui-popover-trigger'
        onClick={() => setIsOpen((current) => !current)}
        type='button'
      >
        {trigger}
      </button>
      {isOpen ? (
        <div aria-label={label} className='ui-popover' role='dialog'>
          {children}
        </div>
      ) : null}
    </div>
  )
}

export function DropdownMenu({
  label,
  trigger,
  children,
}: {
  label: string
  trigger: ReactNode
  children: ReactNode
}) {
  return (
    <Popover label={label} trigger={trigger}>
      {children}
    </Popover>
  )
}

export function Toast({ message, onDismiss }: { message: string; onDismiss?: () => void }) {
  return (
    <div className='ui-toast' role='status'>
      <span>{message}</span>
      {onDismiss ? (
        <button aria-label='Cerrar mensaje' onClick={onDismiss} type='button'>
          ×
        </button>
      ) : null}
    </div>
  )
}
