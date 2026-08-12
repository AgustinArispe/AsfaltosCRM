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
        'flex items-center justify-center gap-3 text-sm font-medium text-slate-600',
        fullscreen ? 'min-h-dvh bg-slate-100 px-6' : 'py-7',
      ].join(' ')}
      role='status'
    >
      <span
        aria-hidden='true'
        className='size-4 animate-spin rounded-full border-2 border-slate-300 border-t-slate-700 motion-reduce:animate-none'
      />
      <span>{label}</span>
    </div>
  )
}
