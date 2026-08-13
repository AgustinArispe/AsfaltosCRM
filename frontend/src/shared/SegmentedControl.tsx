export type Segment = { value: string; label: string; disabled?: boolean }

export function SegmentedControl({
  label,
  value,
  segments,
  onChange,
}: {
  label: string
  value: string
  segments: readonly Segment[]
  onChange: (value: string) => void
}) {
  return (
    <fieldset className='ui-segmented-control'>
      <legend className='sr-only'>{label}</legend>
      {segments.map((segment) => (
        <button
          aria-pressed={segment.value === value}
          className='ui-segmented-control__button'
          disabled={segment.disabled}
          key={segment.value}
          onClick={() => onChange(segment.value)}
          type='button'
        >
          {segment.label}
        </button>
      ))}
    </fieldset>
  )
}
