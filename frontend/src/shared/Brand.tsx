export function Brand({ inverse = false }: { inverse?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <span
        aria-hidden="true"
        className={[
          'grid size-10 place-items-center border text-sm font-bold tracking-tight',
          inverse
            ? 'border-amber-400 bg-amber-400 text-slate-950'
            : 'border-slate-900 bg-slate-900 text-white',
        ].join(' ')}
      >
        FAA
      </span>
      <span className="leading-tight">
        <span
          className={`block text-sm font-semibold ${inverse ? 'text-white' : 'text-slate-950'}`}
        >
          Asfaltos CRM
        </span>
        <span
          className={`block text-xs ${inverse ? 'text-slate-400' : 'text-slate-500'}`}
        >
          Gestión comercial
        </span>
      </span>
    </div>
  )
}
