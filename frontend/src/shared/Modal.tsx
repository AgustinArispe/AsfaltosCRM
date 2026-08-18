import {
  type KeyboardEvent,
  type MouseEvent,
  type ReactNode,
  type SyntheticEvent,
  useEffect,
  useId,
  useRef,
} from 'react'

export function Modal({
  isOpen,
  title,
  description,
  onClose,
  closeDisabled = false,
  size = 'default',
  children,
}: {
  isOpen: boolean
  title: string
  description?: string
  onClose: () => void
  closeDisabled?: boolean
  size?: 'default' | 'large'
  children: ReactNode
}) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)
  const titleId = useId()
  const descriptionId = useId()

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return

    if (isOpen && !dialog.open) {
      previousFocusRef.current = document.activeElement as HTMLElement | null
      dialog.showModal()
      dialog.querySelector<HTMLElement>('[data-modal-initial-focus]')?.focus()
    }

    if (!isOpen && dialog.open) {
      dialog.close()
      previousFocusRef.current?.focus()
      previousFocusRef.current = null
    }
  }, [isOpen])

  useEffect(
    () => () => {
      previousFocusRef.current?.focus()
    },
    [],
  )

  const handleCancel = (event: SyntheticEvent<HTMLDialogElement>) => {
    event.preventDefault()
    if (!closeDisabled) onClose()
  }

  const handleBackdropClick = (event: MouseEvent<HTMLDialogElement>) => {
    if (event.target === event.currentTarget && !closeDisabled) onClose()
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLDialogElement>) => {
    if (event.key !== 'Tab') return
    const dialog = dialogRef.current
    if (!dialog) return
    const focusable = [
      ...dialog.querySelectorAll<HTMLElement>(
        'button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])',
      ),
    ].filter((element) => !element.hasAttribute('hidden'))
    if (focusable.length === 0) {
      event.preventDefault()
      return
    }
    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first.focus()
    }
  }

  return (
    <dialog
      aria-describedby={description ? descriptionId : undefined}
      aria-labelledby={titleId}
      className={`m-auto max-h-[calc(100dvh-2rem)] ${size === 'large' ? 'w-[min(72rem,calc(100%-2rem))]' : 'w-[min(34rem,calc(100%-2rem))]'} border-0 bg-transparent p-0 text-[var(--text-primary)] backdrop:bg-black/55`}
      onCancel={handleCancel}
      onClick={handleBackdropClick}
      onKeyDown={handleKeyDown}
      ref={dialogRef}
    >
      <div className='max-h-[calc(100dvh-2rem)] overflow-y-auto rounded-[var(--radius-overlay)] border border-[var(--subtle-border)] bg-[var(--surface-overlay)] shadow-[var(--shadow-overlay)]'>
        <header className='flex items-start justify-between gap-4 border-b border-[var(--divider)] px-5 py-4 sm:px-6'>
          <div>
            <h2
              className='text-base font-semibold tracking-tight text-[var(--text-primary)]'
              id={titleId}
            >
              {title}
            </h2>
            {description ? (
              <p className='mt-1 text-sm leading-5 text-[var(--text-secondary)]' id={descriptionId}>
                {description}
              </p>
            ) : null}
          </div>
          <button
            aria-label={`Cerrar ${title.toLowerCase()}`}
            className='ui-pressable grid size-11 shrink-0 place-items-center rounded-[var(--radius-control)] text-[var(--text-secondary)] outline-none hover:bg-[var(--hover)] hover:text-[var(--text-primary)] focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)] disabled:cursor-not-allowed disabled:opacity-40'
            disabled={closeDisabled}
            onClick={onClose}
            type='button'
          >
            <svg aria-hidden='true' className='size-5' fill='none' viewBox='0 0 24 24'>
              <path
                d='m6 6 12 12M18 6 6 18'
                stroke='currentColor'
                strokeLinecap='round'
                strokeWidth='1.8'
              />
            </svg>
          </button>
        </header>
        {children}
      </div>
    </dialog>
  )
}
