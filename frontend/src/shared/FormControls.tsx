import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from 'react'

type FieldProps = {
  label: string
  description?: string
  error?: string
  id: string
}

function FieldMessage({ description, error, id }: Omit<FieldProps, 'label'>) {
  if (!description && !error) return null
  return (
    <p className={error ? 'ui-field-error' : 'ui-field-description'} id={`${id}-message`}>
      {error ?? description}
    </p>
  )
}

export function Input({
  label,
  description,
  error,
  id,
  className = '',
  ...props
}: FieldProps & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div className='block'>
      <label className='ui-label' htmlFor={id}>
        {label}
      </label>
      <input
        aria-describedby={description || error ? `${id}-message` : undefined}
        aria-invalid={Boolean(error)}
        className={`ui-field ${className}`}
        id={id}
        {...props}
      />
      <FieldMessage description={description} error={error} id={id} />
    </div>
  )
}

export function Search({ label = 'Buscar', ...props }: Omit<Parameters<typeof Input>[0], 'type'>) {
  return <Input autoComplete='off' type='search' {...props} label={label} />
}

export function Select({
  label,
  description,
  error,
  id,
  className = '',
  children,
  ...props
}: FieldProps & SelectHTMLAttributes<HTMLSelectElement> & { children: ReactNode }) {
  return (
    <div className='block'>
      <label className='ui-label' htmlFor={id}>
        {label}
      </label>
      <select
        aria-describedby={description || error ? `${id}-message` : undefined}
        aria-invalid={Boolean(error)}
        className={`ui-field ${className}`}
        id={id}
        {...props}
      >
        {children}
      </select>
      <FieldMessage description={description} error={error} id={id} />
    </div>
  )
}

export function Checkbox({
  label,
  id,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & FieldProps) {
  return (
    <label
      className='inline-flex min-h-11 items-center gap-2 text-sm text-[var(--text-primary)]'
      htmlFor={id}
    >
      <input className='size-4 accent-[var(--accent-solid)]' id={id} type='checkbox' {...props} />
      {label}
    </label>
  )
}

export function Radio({ label, id, ...props }: InputHTMLAttributes<HTMLInputElement> & FieldProps) {
  return (
    <label
      className='inline-flex min-h-11 items-center gap-2 text-sm text-[var(--text-primary)]'
      htmlFor={id}
    >
      <input className='size-4 accent-[var(--accent-solid)]' id={id} type='radio' {...props} />
      {label}
    </label>
  )
}
