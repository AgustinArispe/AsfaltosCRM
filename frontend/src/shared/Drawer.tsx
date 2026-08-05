import {
  useEffect,
  useId,
  useRef,
  useState,
  type MouseEvent,
  type ReactNode,
  type SyntheticEvent,
} from 'react'

const CLOSE_DURATION_MS = 160

export function Drawer({
  isOpen,
  title,
  description,
  onClose,
  onAfterClose,
  closeDisabled = false,
  children,
}: {
  isOpen: boolean
  title: string
  description?: string
  onClose: () => void
  onAfterClose?: () => void
  closeDisabled?: boolean
  children: ReactNode
}) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)
  const closeTimerRef = useRef<number | null>(null)
  const onAfterCloseRef = useRef(onAfterClose)
  const [isClosing, setIsClosing] = useState(false)
  const titleId = useId()
  const descriptionId = useId()

  useEffect(() => {
    onAfterCloseRef.current = onAfterClose
  }, [onAfterClose])

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return

    if (closeTimerRef.current !== null) {
      window.clearTimeout(closeTimerRef.current)
      closeTimerRef.current = null
    }

    if (isOpen) {
      setIsClosing(false)
      if (!dialog.open) {
        previousFocusRef.current = document.activeElement as HTMLElement | null
        dialog.showModal()
        dialog
          .querySelector<HTMLElement>('[data-drawer-initial-focus]')
          ?.focus()
      }
      return
    }

    if (dialog.open) {
      const reduceMotion = window.matchMedia?.(
        '(prefers-reduced-motion: reduce)',
      ).matches
      setIsClosing(true)
      closeTimerRef.current = window.setTimeout(
        () => {
          dialog.close()
          setIsClosing(false)
          previousFocusRef.current?.focus()
          previousFocusRef.current = null
          closeTimerRef.current = null
          onAfterCloseRef.current?.()
        },
        reduceMotion ? 0 : CLOSE_DURATION_MS,
      )
    }
  }, [isOpen])

  useEffect(
    () => () => {
      if (closeTimerRef.current !== null) {
        window.clearTimeout(closeTimerRef.current)
      }
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
      className="drawer-dialog text-slate-900"
      data-closing={isClosing ? 'true' : 'false'}
      onCancel={handleCancel}
      onClick={handleBackdropClick}
      ref={dialogRef}
    >
      <div className="drawer-panel flex flex-col border-l border-slate-200">
        <header className="flex shrink-0 items-start justify-between gap-4 border-b border-slate-200 bg-white px-4 py-3 sm:px-5">
          <div className="min-w-0 py-1">
            <h2 className="truncate text-base font-semibold text-slate-950" id={titleId}>
              {title}
            </h2>
            {description ? (
              <p className="mt-0.5 text-sm text-slate-600" id={descriptionId}>
                {description}
              </p>
            ) : null}
          </div>
          <button
            aria-label={`Cerrar ${title.toLowerCase()}`}
            className="ui-pressable grid size-11 shrink-0 place-items-center rounded-[4px] text-slate-500 outline-none hover:bg-slate-100 hover:text-slate-900 focus-visible:ring-2 focus-visible:ring-slate-500 disabled:opacity-40"
            data-drawer-initial-focus
            disabled={closeDisabled}
            onClick={onClose}
            type="button"
          >
            <svg aria-hidden="true" className="size-5" fill="none" viewBox="0 0 24 24">
              <path d="m6 6 12 12M18 6 6 18" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" />
            </svg>
          </button>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
      </div>
    </dialog>
  )
}
