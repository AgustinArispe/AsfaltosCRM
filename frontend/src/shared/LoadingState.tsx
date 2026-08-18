export function LoadingState({
  label,
  fullscreen = false,
}: {
  label: string
  fullscreen?: boolean
}) {
  return (
    <div
      aria-busy='true'
      className={[
        'flex items-center justify-center gap-3 text-sm font-medium text-[var(--text-secondary)]',
        fullscreen ? 'min-h-dvh bg-[var(--surface-secondary)] px-6' : 'py-7',
      ].join(' ')}
      role='status'
    >
      <span
        aria-hidden='true'
        className='size-4 animate-spin rounded-full border-2 border-[var(--subtle-border)] border-t-[var(--strong-border)] motion-reduce:animate-none'
      />
      <span>{label}</span>
    </div>
  )
}
