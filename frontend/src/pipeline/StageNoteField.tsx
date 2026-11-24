import { type Ref, useId } from 'react'
import { CustomerNoteField } from '../customers/CustomerNoteField'

export function StageNoteField({
  value,
  onChange,
  customerNote,
  onCustomerNoteChange,
  disabled = false,
  inputRef,
}: {
  value: string
  onChange: (value: string) => void
  customerNote: string
  onCustomerNoteChange: (value: string) => void
  disabled?: boolean
  inputRef?: Ref<HTMLTextAreaElement>
}) {
  const id = useId()
  return (
    <div className='space-y-2'>
      <label className='ui-label' htmlFor={id}>
        Nota del cambio de estado (recomendada)
      </label>
      <textarea
        aria-describedby={`${id}-help`}
        className='ui-field min-h-20 resize-y py-2.5 text-base'
        disabled={disabled}
        id={id}
        maxLength={4000}
        onChange={(event) => onChange(event.target.value)}
        ref={inputRef}
        value={value}
      />
      <p className='text-xs leading-5 text-[var(--text-secondary)]' id={`${id}-help`}>
        Si hubo un acuerdo o un próximo paso, dejalo en el historial.
        <span className='ml-2 tabular-nums'>{value.length}/4000</span>
      </p>
      <details className='rounded-[var(--radius-control)] border border-[var(--divider)] px-3 py-2'>
        <summary className='ui-label cursor-pointer'>
          {customerNote.trim()
            ? 'Nota del cliente lista para guardar'
            : 'Agregar un dato para recordar (opcional)'}
        </summary>
        <div className='mt-2'>
          <CustomerNoteField
            disabled={disabled}
            onChange={onCustomerNoteChange}
            value={customerNote}
          />
        </div>
      </details>
    </div>
  )
}
