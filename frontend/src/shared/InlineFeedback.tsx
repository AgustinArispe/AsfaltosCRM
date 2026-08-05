export function InlineFeedback({
  message,
  onDismiss,
}: {
  message: string
  onDismiss?: () => void
}) {
  return (
    <div
      className="flex items-start justify-between gap-4 rounded-[4px] border border-rose-200 border-l-2 border-l-rose-500 bg-rose-50 px-3 py-2.5 text-sm font-medium text-rose-900"
      role="alert"
    >
      <p>{message}</p>
      {onDismiss ? (
        <button
          className="min-h-11 shrink-0 rounded-[4px] px-2 underline decoration-rose-300 underline-offset-2 outline-none hover:decoration-rose-700 focus-visible:ring-2 focus-visible:ring-rose-600"
          onClick={onDismiss}
          type="button"
        >
          Cerrar
        </button>
      ) : null}
    </div>
  )
}
