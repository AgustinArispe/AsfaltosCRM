export function Brand({
  inverse = false,
  collapsed = false,
}: {
  inverse?: boolean
  collapsed?: boolean
}) {
  return (
    <div className='flex items-center gap-2.5'>
      <img
        alt=''
        className='size-9 shrink-0 rounded-[var(--radius-control)] shadow-[var(--shadow-subtle)]'
        height={36}
        src='/pulse-mark.svg'
        width={36}
      />
      <span className={collapsed ? 'sr-only' : 'leading-tight'}>
        <span
          className={`block text-sm font-semibold ${inverse ? 'text-[var(--on-brand)]' : 'text-[var(--text-primary)]'}`}
        >
          PULSE CRM
        </span>
        <span
          className={`block text-[0.6875rem] ${inverse ? 'text-[var(--text-tertiary)]' : 'text-[var(--text-tertiary)]'}`}
        >
          Seguí el ritmo de tus ventas
        </span>
      </span>
    </div>
  )
}
