export function Brand({ inverse = false }: { inverse?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <span
        aria-hidden="true"
        className={[
          'grid size-9 place-items-center rounded-[4px] border text-xs font-bold tracking-[0.04em]',
          inverse
            ? 'border-slate-500 bg-slate-100 text-slate-900'
            : 'border-slate-900 bg-slate-900 text-white',
        ].join(' ')}
      >
        FAA
      </span>
      <span className="leading-tight">
        <span
          className={`block text-sm font-semibold ${inverse ? 'text-slate-100' : 'text-slate-950'}`}
        >
          Asfaltos CRM
        </span>
        <span
          className={`block text-[0.6875rem] ${inverse ? 'text-slate-400' : 'text-slate-500'}`}
        >
          Gestión comercial
        </span>
      </span>
    </div>
  )
}
