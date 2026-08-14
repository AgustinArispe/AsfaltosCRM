import { activeFilterCount, type PipelineFilters, type PipelineSort } from './board-state'
import type { LeadSource } from './types'

const SORT_OPTIONS: readonly { value: PipelineSort; label: string }[] = [
  { value: 'newest', label: 'Más recientes' },
  { value: 'oldest', label: 'Más antiguas' },
  { value: 'stage-oldest', label: 'Más tiempo en etapa' },
  { value: 'stage-newest', label: 'Menos tiempo en etapa' },
]

const SOURCE_OPTIONS: readonly { value: LeadSource; label: string }[] = [
  { value: 'WEB', label: 'Web' },
  { value: 'WHATSAPP', label: 'WhatsApp' },
]

export function PipelineControls({
  filters,
  productOptions,
  showStageAge,
  onFiltersChange,
  onShowStageAgeChange,
  onReset,
}: {
  filters: PipelineFilters
  productOptions: { id: number; name: string }[]
  showStageAge: boolean
  onFiltersChange: (filters: PipelineFilters) => void
  onShowStageAgeChange: (value: boolean) => void
  onReset: () => void
}) {
  const activeCount = activeFilterCount(filters, showStageAge)
  return (
    <form
      aria-label='Filtros del pipeline'
      className='pipeline-controls'
      onSubmit={(event) => event.preventDefault()}
    >
      <label className='pipeline-search'>
        <span className='sr-only'>Buscar oportunidades</span>
        <input
          className='ui-field'
          onChange={(event) => onFiltersChange({ ...filters, search: event.target.value })}
          placeholder='Buscar'
          type='search'
          value={filters.search}
        />
      </label>
      <label className='pipeline-control-label'>
        <span>Orden</span>
        <select
          className='ui-field'
          onChange={(event) =>
            onFiltersChange({ ...filters, sort: event.target.value as PipelineSort })
          }
          value={filters.sort}
        >
          {SORT_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
      <label className='pipeline-control-label'>
        <span>Origen</span>
        <select
          className='ui-field'
          onChange={(event) =>
            onFiltersChange({ ...filters, source: event.target.value as PipelineFilters['source'] })
          }
          value={filters.source}
        >
          <option value='ALL'>Todos los orígenes</option>
          {SOURCE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
      <details className='pipeline-more-filters'>
        <summary>Más filtros{activeCount ? ` · ${activeCount}` : ''}</summary>
        <div className='pipeline-more-filters__content'>
          <label className='pipeline-control-label'>
            <span>Producto</span>
            <select
              className='ui-field'
              onChange={(event) => onFiltersChange({ ...filters, productId: event.target.value })}
              value={filters.productId}
            >
              <option value='ALL'>Todos los productos</option>
              {productOptions.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.name}
                </option>
              ))}
            </select>
          </label>
          <label className='pipeline-stage-age-toggle'>
            <input
              checked={showStageAge}
              onChange={(event) => onShowStageAgeChange(event.target.checked)}
              type='checkbox'
            />
            Mostrar antigüedad de etapa
          </label>
        </div>
      </details>
      {activeCount ? (
        <button className='pipeline-reset' onClick={onReset} type='button'>
          Limpiar
        </button>
      ) : null}
    </form>
  )
}
