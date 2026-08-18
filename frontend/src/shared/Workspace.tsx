import type {
  FormHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
} from 'react'

import { Icon } from './Icon'

export function WorkspaceHeader({
  title,
  description,
  actions,
  titleId,
}: {
  title: string
  description?: string
  actions?: ReactNode
  titleId: string
}) {
  return (
    <header className='ui-workspace-header'>
      <div>
        <h2 id={titleId}>{title}</h2>
        {description ? <p>{description}</p> : null}
      </div>
      {actions ? (
        <div className='flex flex-wrap items-center justify-end gap-2'>{actions}</div>
      ) : null}
    </header>
  )
}

export function Toolbar({
  children,
  className = '',
  ...props
}: FormHTMLAttributes<HTMLFormElement> & { children: ReactNode }) {
  return (
    <form
      className={`ui-toolbar ui-toolbar--divided ${className}`}
      onSubmit={(event) => event.preventDefault()}
      {...props}
    >
      {children}
    </form>
  )
}

export function SearchField({
  label,
  className = '',
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  return (
    <label className={`ui-search-field ${className}`}>
      <span className='sr-only'>{label}</span>
      <Icon name='search' />
      <input aria-label={label} className='ui-field' type='search' {...props} />
    </label>
  )
}

export function FilterControl({
  label,
  children,
  className = '',
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & {
  label: string
  children: ReactNode
}) {
  return (
    <label>
      <span className='sr-only'>{label}</span>
      <select aria-label={label} className={`ui-filter-control ${className}`} {...props}>
        {children}
      </select>
    </label>
  )
}
