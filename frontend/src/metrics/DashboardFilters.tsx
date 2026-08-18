import type { ReactNode } from 'react'

import type { Product } from '../products/types'
import { Select } from '../shared/FormControls'
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
  const customRange = filters.preset === 'custom'

  return (
    <Toolbar
      aria-label='Filtros del Dashboard'
      className='dashboard-filters'
      onSubmit={(event) => event.preventDefault()}
    >
      <FilterControl
        id='dashboard-period'
        label='Período'
        onChange={(event) => {
          const value = event.target.value as DashboardFiltersModel['preset']
          if (value === 'custom') {
            onChange({ ...filters, preset: value })
            return
          }
          onChange(filtersForPreset(value, filters))
        }}
        value={filters.preset}
      >
        <option value='month'>Este mes</option>
        <option value='last-three-months'>Últimos 3 meses</option>
        <option value='year'>Este año</option>
        <option value='custom'>Personalizado</option>
      </FilterControl>
      <FilterControl
        id='dashboard-source'
        label='Origen'
        onChange={(event) =>
          onChange({
            ...filters,
            source: event.target.value ? (event.target.value as 'WEB' | 'WHATSAPP') : null,
          })
        }
        value={filters.source ?? ''}
      >
        <option value=''>Todos los orígenes</option>
        <option value='WEB'>{sourceLabel('WEB')}</option>
        <option value='WHATSAPP'>{sourceLabel('WHATSAPP')}</option>
      </FilterControl>
      {customRange ? (
        <div className='dashboard-custom-range'>
          <label className='dashboard-filter-field' htmlFor='dashboard-from'>
            <span>Desde</span>
            <input
              id='dashboard-from'
              max={filters.customEnd}
              onChange={(event) =>
                onChange(filtersForCustomRange(filters, event.target.value, filters.customEnd))
              }
              type='date'
              value={filters.customStart}
            />
          </label>
          <label className='dashboard-filter-field' htmlFor='dashboard-to'>
            <span>Hasta</span>
            <input
              id='dashboard-to'
              min={filters.customStart}
              onChange={(event) =>
                onChange(filtersForCustomRange(filters, filters.customStart, event.target.value))
              }
              type='date'
              value={filters.customEnd}
            />
          </label>
        </div>
      ) : null}
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
          <p className='dashboard-filter-hint'>
            Los filtros se aplican a todas las métricas disponibles.
          </p>
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
