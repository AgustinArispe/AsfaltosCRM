export function LegendaryBadge() {
  return (
    <span className="inline-flex items-center gap-1.5 border border-amber-200 bg-amber-50 px-2 py-1 text-xs font-bold text-amber-900">
      <svg
        aria-hidden="true"
        className="size-3.5 fill-amber-500"
        viewBox="0 0 20 20"
      >
        <path d="m10 1.8 2.45 4.97 5.49.8-3.97 3.86.94 5.47L10 14.32 5.09 16.9l.94-5.47-3.97-3.86 5.49-.8L10 1.8Z" />
      </svg>
      Legendario
    </span>
  )
}
