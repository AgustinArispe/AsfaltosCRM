export function InlineFeedback({
  message,
  onDismiss,
}: {
  message: string
  onDismiss?: () => void
}) {
  return (
    <div
      className='flex items-start justify-between gap-4 rounded-[var(--radius-control)] border border-[var(--destructive-border)] bg-[var(--destructive-subtle)] px-3 py-2.5 text-sm font-medium text-[var(--destructive-text)]'
      role='alert'
    >
      <p>{message}</p>
      {onDismiss ? (
        <button
          className='min-h-11 shrink-0 rounded-[var(--radius-control)] px-2 underline decoration-[var(--destructive-border)] underline-offset-2 outline-none hover:decoration-[var(--destructive-text)] focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]'
          onClick={onDismiss}
          type='button'
        >
          Cerrar
        </button>
      ) : null}
    </div>
  )
}
