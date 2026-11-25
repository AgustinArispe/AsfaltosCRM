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
    <fieldset aria-describedby={`${id}-optional`} className='min-w-0 space-y-3'>
      <legend className='text-sm font-semibold text-[var(--text-primary)]'>
        Notas recomendadas
      </legend>
      <p className='text-xs leading-5 text-[var(--text-secondary)]' id={`${id}-optional`}>
        Podés continuar sin completarlas.
      </p>
      <div>
        <label className='ui-label' htmlFor={id}>
          Nota de la oportunidad
        </label>
        <p className='text-xs leading-5 text-[var(--text-secondary)]' id={`${id}-help`}>
          Qué se acordó o cuál es el próximo paso.
        </p>
        <textarea
          aria-describedby={`${id}-help`}
          className='ui-field mt-1 min-h-14 resize-y py-2 text-base'
          disabled={disabled}
          id={id}
          maxLength={4000}
          onChange={(event) => onChange(event.target.value)}
          placeholder='Ej. El viernes confirma la cantidad.'
          ref={inputRef}
          rows={2}
          value={value}
        />
      </div>
      <CustomerNoteField
        disabled={disabled}
        inStageChange
        onChange={onCustomerNoteChange}
        value={customerNote}
      />
    </fieldset>
  )
}
