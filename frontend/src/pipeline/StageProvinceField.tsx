import { useId } from 'react'

export function StageProvinceField({
  currentProvince,
  value,
  onChange,
  disabled,
}: {
  currentProvince?: string | null
  value: string
  onChange: (value: string) => void
  disabled?: boolean
}) {
  const id = useId()
  if (currentProvince?.trim()) return null
  return (
    <div className='mt-4 rounded-[var(--radius-control)] border border-[var(--border-subtle)] p-4'>
      <label className='ui-label' htmlFor={id}>
        Provincia (opcional, recomendada)
      </label>
      <p className='mt-1 text-sm text-[var(--text-secondary)]' id={`${id}-help`}>
        Este cliente todavía no tiene provincia. Si la conocés, completala para mejorar el
        seguimiento. Si no, podés continuar sin este dato.
      </p>
      <input
        aria-describedby={`${id}-help`}
        autoComplete='address-level1'
        className='ui-field mt-3'
        disabled={disabled}
        id={id}
        onChange={(event) => onChange(event.target.value)}
        placeholder='Ej.: Buenos Aires'
        type='text'
        value={value}
      />
    </div>
  )
}
