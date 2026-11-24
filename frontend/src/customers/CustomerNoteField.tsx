import { type Ref, useId } from 'react'

export function CustomerNoteField({
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
    <div>
      <label className='ui-label' htmlFor={id}>
        Nota del cliente
      </label>
      <textarea
        aria-describedby={`${id}-help`}
        className='ui-field mt-1 min-h-20 resize-y py-2 text-base'
        disabled={disabled}
        id={id}
        maxLength={600}
        onChange={(event) => onChange(event.target.value)}
        placeholder='Ej. Prefiere coordinar las entregas por WhatsApp.'
        ref={inputRef}
        value={value}
      />
      <p className='mt-1 text-xs leading-5 text-[var(--text-secondary)]' id={`${id}-help`}>
        ¿Qué conviene recordar la próxima vez que hablen?
      </p>
    </div>
  )
}
