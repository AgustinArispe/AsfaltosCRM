export function InlineFeedback({
  message,
  onDismiss,
}: {
  message: string
  onDismiss?: () => void
}) {
  return (
    <div
      className="flex items-start justify-between gap-4 border-l-2 border-red-600 bg-red-50 px-3 py-2.5 text-sm font-medium text-red-900"
      role="alert"
    >
      <p>{message}</p>
      {onDismiss ? (
        <button
          className="min-h-11 shrink-0 px-2 underline decoration-red-300 underline-offset-2 outline-none hover:decoration-red-700 focus-visible:ring-2 focus-visible:ring-red-600"
          onClick={onDismiss}
          type="button"
        >
          Cerrar
        </button>
      ) : null}
    </div>
  )
}
