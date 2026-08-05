export function PlaceholderPage({
  title,
  description,
}: {
  title: string
  description: string
}) {
  return (
    <section className="ui-panel max-w-3xl border-t-2 border-t-slate-400 px-5 py-6 sm:px-6" aria-labelledby="placeholder-title">
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
        {title}
      </p>
      <h2 className="mt-2 text-lg font-semibold text-slate-950" id="placeholder-title">
        Módulo en preparación
      </h2>
      <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
    </section>
  )
}
