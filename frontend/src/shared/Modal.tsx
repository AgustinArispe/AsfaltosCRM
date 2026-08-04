import {
  useEffect,
  useId,
  useRef,
  type MouseEvent,
  type ReactNode,
  type SyntheticEvent,
} from 'react'

export function Modal({
  isOpen,
  title,
  description,
  onClose,
  closeDisabled = false,
  children,
}: {
  isOpen: boolean
  title: string
  description?: string
  onClose: () => void
  closeDisabled?: boolean
  children: ReactNode
}) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)
  const titleId = useId()
  const descriptionId = useId()

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return

    let focusTimeoutId: number | undefined

    if (isOpen && !dialog.open) {
      previousFocusRef.current = document.activeElement as HTMLElement | null
      dialog.showModal()
      focusTimeoutId = window.setTimeout(() => {
        dialog
          .querySelector<HTMLElement>('[data-modal-initial-focus]')
          ?.focus()
      }, 0)
      return () => window.clearTimeout(focusTimeoutId)
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

  return (
    <dialog
      aria-describedby={description ? descriptionId : undefined}
      aria-labelledby={titleId}
      className="m-auto w-[min(34rem,calc(100%-2rem))] border-0 bg-transparent p-0 text-slate-900 backdrop:bg-slate-950/60"
      onCancel={handleCancel}
      onClick={handleBackdropClick}
      ref={dialogRef}
    >
      <div className="border border-slate-200 bg-white shadow-2xl">
        <header className="flex items-start justify-between gap-4 border-b border-slate-200 px-5 py-4">
          <div>
            <h2 className="text-lg font-semibold tracking-tight text-slate-950" id={titleId}>
              {title}
            </h2>
            {description ? (
              <p className="mt-1 text-sm leading-5 text-slate-600" id={descriptionId}>
                {description}
              </p>
            ) : null}
          </div>
          <button
            aria-label={`Cerrar ${title.toLowerCase()}`}
            className="grid size-11 shrink-0 place-items-center text-slate-500 outline-none transition-colors duration-150 hover:bg-slate-100 hover:text-slate-900 focus-visible:ring-2 focus-visible:ring-amber-500 disabled:cursor-not-allowed disabled:opacity-40 motion-reduce:transition-none"
            disabled={closeDisabled}
            onClick={onClose}
            type="button"
          >
            <svg aria-hidden="true" className="size-5" fill="none" viewBox="0 0 24 24">
              <path d="m6 6 12 12M18 6 6 18" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" />
            </svg>
          </button>
        </header>
        {children}
      </div>
    </dialog>
  )
}
