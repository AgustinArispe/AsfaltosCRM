import { Badge } from '../shared/Badge'
import { Button } from '../shared/Button'
import { Icon } from '../shared/Icon'
import type { Product } from './types'

function ProductStatus({ isActive }: { isActive: boolean }) {
  return (
    <Badge tone={isActive ? 'active' : 'neutral'}>
      <span
        aria-hidden='true'
        className={
          isActive
            ? 'size-1.5 rounded-full bg-[var(--success-text)]'
            : 'size-1.5 rounded-full bg-[var(--text-tertiary)]'
        }
      />
      {isActive ? 'Activo' : 'Inactivo'}
    </Badge>
  )
}

export function ProductTable({
  products,
  canManage,
  busyProductIds,
  onEdit,
  onDeactivate,
  onReactivate,
}: {
  products: Product[]
  canManage: boolean
  busyProductIds: Set<number>
  onEdit: (product: Product) => void
  onDeactivate: (product: Product) => void
  onReactivate: (product: Product) => void
}) {
  return (
    <section aria-label='Listado de productos FAA' className='product-records'>
      <ul className='workspace-record-list'>
        {products.map((product) => {
          const isBusy = busyProductIds.has(product.id)
          return (
            <li
              aria-label={`Producto ${product.name}`}
              className={`workspace-record-card product-record ${product.is_active ? '' : 'product-record--inactive'}`}
              key={product.id}
            >
              <span className='workspace-record-icon product-record__icon'>
                <Icon name='products' />
              </span>
              <span className='workspace-record-identity'>
                <strong>{product.name}</strong>
                <span>Producto FAA</span>
              </span>
              <ProductStatus isActive={product.is_active} />
              {canManage ? (
                <div className='workspace-record-actions'>
                  <Button
                    aria-label={`Editar ${product.name}`}
                    disabled={isBusy}
                    onClick={() => onEdit(product)}
                    size='compact'
                    variant='ghost'
                  >
                    <Icon name='pencil' />
                    Editar
                  </Button>
                  {product.is_active ? (
                    <Button
                      aria-label={`Desactivar ${product.name}`}
                      className='text-[var(--destructive-text)] hover:bg-[var(--destructive-subtle)] hover:text-[var(--destructive-text)]'
                      disabled={isBusy}
                      onClick={() => onDeactivate(product)}
                      size='compact'
                      variant='ghost'
                    >
                      Desactivar
                    </Button>
                  ) : (
                    <Button
                      aria-label={`Reactivar ${product.name}`}
                      disabled={isBusy}
                      onClick={() => onReactivate(product)}
                      size='compact'
                    >
                      {isBusy ? 'Reactivando…' : 'Reactivar'}
                    </Button>
                  )}
                </div>
              ) : null}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
