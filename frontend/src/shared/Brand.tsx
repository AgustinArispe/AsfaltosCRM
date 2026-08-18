export function Brand({
  inverse = false,
  collapsed = false,
}: {
  inverse?: boolean
  collapsed?: boolean
}) {
  return (
    <div className='flex items-center gap-2.5'>
      <span
        aria-hidden='true'
        className={[
          'grid size-9 place-items-center rounded-[var(--radius-control)] border text-xs font-bold tracking-[0.04em]',
          inverse
            ? 'border-[var(--strong-border)] bg-[var(--surface-secondary)] text-[var(--text-primary)]'
            : 'border-[var(--brand-deep)] bg-[var(--brand-deep)] text-[var(--on-brand)]',
        ].join(' ')}
      >
        FAA
      </span>
      <span className={collapsed ? 'sr-only' : 'leading-tight'}>
        <span
          className={`block text-sm font-semibold ${inverse ? 'text-[var(--on-brand)]' : 'text-[var(--text-primary)]'}`}
        >
          Asfaltos CRM
        </span>
        <span
          className={`block text-[0.6875rem] ${inverse ? 'text-[var(--text-tertiary)]' : 'text-[var(--text-tertiary)]'}`}
        >
          Gestión comercial
        </span>
      </span>
    </div>
  )
}
