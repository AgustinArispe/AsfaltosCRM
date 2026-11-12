import { type Ref, useId } from 'react'

export function StageNoteField({
  value,
  onChange,
  disabled = false,
  inputRef,
}: {
  value: string
  onChange: (value: string) => void
  disabled?: boolean
  inputRef?: Ref<HTMLTextAreaElement>
}) {
  const id = useId()
  return (
    <div className='space-y-2'>
      <label className='ui-label' htmlFor={id}>
        Nota del cambio de estado (obligatoria)
      </label>
      <textarea
        aria-describedby={`${id}-help`}
        className='ui-field min-h-28 resize-y py-2.5 text-base'
        disabled={disabled}
        id={id}
        maxLength={4000}
        onChange={(event) => onChange(event.target.value)}
        required
        ref={inputRef}
        value={value}
      />
      <p className='text-xs leading-5 text-[var(--text-secondary)]' id={`${id}-help`}>
        Explicá qué se hizo o acordó. Quedará en el historial de la oportunidad y del cliente.
        <span className='ml-2 tabular-nums'>{value.length}/4000</span>
      </p>
    </div>
  )
}
