import { type Dispatch, type ReactNode, type SetStateAction, useId, useState } from 'react'
import { SOURCE_LABELS } from '../pipeline/config'
import type { WonFilterOptions, WonFilters } from '../won/types'
import { Button } from './Button'
import { Input, Select } from './FormControls'
import { Icon } from './Icon'
import { PeriodFilter } from './PeriodFilter'

export function ClosedOpportunityFilters<T extends WonFilters>({
  activeExtraFilters = 0,
  apply,
  children,
  draft,
  label,
  options,
  resetFilters,
  setDraft,
  surface,
}: {
  activeExtraFilters?: number
  apply: () => void
  children?: ReactNode
  draft: T
  label: string
  options: WonFilterOptions | null
  resetFilters: () => void
  setDraft: Dispatch<SetStateAction<T>>
  surface: 'won' | 'lost'
}) {
  const compact = surface === 'lost'
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [periodReset, setPeriodReset] = useState(0)
  const advancedId = useId()
  const advancedFields = (
    <>
      <div className='won-filter'>
        <Select
          id={`${surface}-product`}
          label='Producto'
          value={draft.product}
          onChange={(event) => setDraft({ ...draft, product: event.target.value })}
        >
          <option value=''>Todos</option>
          {options?.products.map((option) => (
            <option key={option.id} value={option.id}>
              {option.name}
              {option.is_active ? '' : ' (inactivo)'}
            </option>
          ))}
        </Select>
      </div>
      <div className='won-filter'>
        <Select
          id={`${surface}-source`}
          label='Origen'
          value={draft.source}
          onChange={(event) =>
            setDraft({ ...draft, source: event.target.value as WonFilters['source'] })
          }
        >
          <option value=''>Todos</option>
          {Object.entries(SOURCE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
      </div>
      <div className='won-filter'>
        <Select
          id={`${surface}-province`}
          label='Provincia'
          value={draft.province}
          onChange={(event) => setDraft({ ...draft, province: event.target.value })}
        >
          <option value=''>Todas</option>
          {options?.provinces.map((value) => (
            <option key={value}>{value}</option>
          ))}
        </Select>
      </div>
      <div className='won-filter'>
        <Select
          id={`${surface}-responsible`}
          label='Responsable'
          value={draft.unassigned ? 'unassigned' : draft.responsible}
          onChange={(event) =>
            setDraft({
              ...draft,
              responsible: event.target.value === 'unassigned' ? '' : event.target.value,
              unassigned: event.target.value === 'unassigned',
            })
          }
        >
          <option value=''>Todos</option>
          <option value='unassigned'>Sin responsable</option>
          {options?.responsible_users.map((option) => (
            <option key={option.id} value={option.id}>
              {option.full_name}
              {option.is_active ? '' : ' (inactivo)'}
            </option>
          ))}
        </Select>
      </div>
      {children}
    </>
  )
  return (
    <form
      aria-label={label}
      className={compact ? 'won-filters closed-filters' : 'won-filters'}
      onSubmit={(event) => {
        event.preventDefault()
        apply()
      }}
    >
      <PeriodFilter
        compact={compact}
        key={periodReset}
        value={{ preset: draft.period, from: draft.from, to: draft.to }}
        onChange={(selection) =>
          setDraft((current) => ({
            ...current,
            period: selection.preset,
            from: selection.from,
            to: selection.to,
          }))
        }
      />
      <div className='won-filter won-filter--search'>
        <Icon className='won-filter__search-icon' name='search' />
        <Input
          className='won-filter__search-input'
          id={`${surface}-search`}
          label='Buscar cliente, empresa o ID'
          value={draft.search}
          onChange={(event) => setDraft({ ...draft, search: event.target.value })}
        />
      </div>
      {compact ? (
        <>
          <div className='closed-filter-tools'>
            <Button
              aria-controls={advancedId}
              aria-expanded={advancedOpen}
              onClick={() => setAdvancedOpen((open) => !open)}
              variant='ghost'
            >
              <Icon name='filter' />
              Filtros adicionales{activeExtraFilters ? ` (${activeExtraFilters})` : ''}
              <Icon
                className={advancedOpen ? 'size-4 -rotate-90' : 'size-4 rotate-90'}
                name='chevron-right'
              />
            </Button>
          </div>
          <div className='closed-filter-details' hidden={!advancedOpen} id={advancedId}>
            {advancedFields}
          </div>
        </>
      ) : (
        advancedFields
      )}
      <div className='won-filter-actions'>
        <Button size='compact' type='submit'>
          {compact ? null : <Icon name='filter' />}
          Aplicar
        </Button>
        <Button
          size='compact'
          type='button'
          variant='ghost'
          onClick={() => {
            if (compact) setPeriodReset((current) => current + 1)
            resetFilters()
          }}
        >
          Restablecer
        </Button>
      </div>
    </form>
  )
}
