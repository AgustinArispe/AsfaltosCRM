import type { ReactNode } from 'react'
import { SOURCE_OPTIONS } from '../pipeline/config'
import type { LeadSource } from '../pipeline/types'
import type { Product } from '../products/types'
import { Select } from '../shared/FormControls'
import { PeriodFilter } from '../shared/PeriodFilter'
import { FilterControl, Toolbar } from '../shared/Workspace'
import type { DashboardFilters as DashboardFiltersModel } from './filters'
import { activeFilterCount, filtersForCustomRange, filtersForPreset, sourceLabel } from './filters'

export function DashboardFilters({
  filters,
  products,
  provinces,
  onChange,
  onReset,
  action,
}: {
  filters: DashboardFiltersModel
  products: Product[]
  provinces: string[]
  onChange: (filters: DashboardFiltersModel) => void
  onReset: () => void
  action?: ReactNode
}) {
  const count = activeFilterCount(filters)

  return (
    <Toolbar
      aria-label='Filtros del Dashboard'
      className='dashboard-filters'
      onSubmit={(event) => event.preventDefault()}
    >
      <PeriodFilter
        value={{
          preset: filters.preset === 'last-three-months' ? 'three-months' : filters.preset,
          from: filters.customStart,
          to: filters.customEnd,
        }}
        onChange={(selection) =>
          onChange(
            selection.preset === 'custom'
              ? filtersForCustomRange(filters, selection.from, selection.to)
              : filtersForPreset(selection.preset, filters),
          )
        }
      />
      <FilterControl
        id='dashboard-source'
        label='Origen'
        onChange={(event) =>
          onChange({
            ...filters,
            source: event.target.value ? (event.target.value as LeadSource) : null,
          })
        }
        value={filters.source ?? ''}
      >
        <option value=''>Todos los orígenes</option>
        {SOURCE_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {sourceLabel(option.value)}
          </option>
        ))}
      </FilterControl>
      <details className='dashboard-more-filters'>
        <summary>Filtros{count > 0 ? ` · ${count}` : ''}</summary>
        <div className='dashboard-more-filters__content'>
          <Select
            id='dashboard-product'
            label='Producto'
            onChange={(event) =>
              onChange({
                ...filters,
                productId: event.target.value ? Number(event.target.value) : null,
              })
            }
            value={filters.productId?.toString() ?? ''}
          >
            <option value=''>Todos los productos</option>
            {products.map((product) => (
              <option key={product.id} value={product.id}>
                {product.name}
                {product.is_active ? '' : ' (inactivo)'}
              </option>
            ))}
          </Select>
          <Select
            id='dashboard-province'
            label='Provincia'
            onChange={(event) => onChange({ ...filters, province: event.target.value || null })}
            value={filters.province ?? ''}
          >
            <option value=''>Todas las provincias</option>
            {provinces.map((province) => (
              <option key={province} value={province}>
                {province}
              </option>
            ))}
          </Select>
        </div>
      </details>
      {count > 0 ? (
        <button className='dashboard-filter-reset' onClick={onReset} type='button'>
          Restablecer
        </button>
      ) : null}
      {action ? <div className='ml-auto'>{action}</div> : null}
    </Toolbar>
  )
}
