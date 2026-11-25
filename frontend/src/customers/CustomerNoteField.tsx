import { type Ref, useId } from 'react'

export function CustomerNoteField({
  value,
  onChange,
  disabled = false,
  inputRef,
  inStageChange = false,
}: {
  value: string
  onChange: (value: string) => void
  disabled?: boolean
  inputRef?: Ref<HTMLTextAreaElement>
  inStageChange?: boolean
}) {
  const id = useId()
  return (
    <div>
      <label className='ui-label' htmlFor={id}>
        {inStageChange ? 'Para recordar del cliente' : 'Nota del cliente'}
      </label>
      <p className='text-xs leading-5 text-[var(--text-secondary)]' id={`${id}-help`}>
        {inStageChange
          ? 'Preferencias o detalles útiles para futuras conversaciones.'
          : '¿Qué conviene recordar la próxima vez que hablen?'}
      </p>
      <textarea
        aria-describedby={`${id}-help`}
        className={`ui-field mt-1 resize-y py-2 text-base ${inStageChange ? 'min-h-14' : 'min-h-20'}`}
        disabled={disabled}
        id={id}
        maxLength={600}
        onChange={(event) => onChange(event.target.value)}
        placeholder='Ej. Prefiere mensajes después de las 15.'
        ref={inputRef}
        rows={2}
        value={value}
      />
    </div>
  )
}
