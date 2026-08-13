import { Badge } from '../shared/Badge'
import { Button } from '../shared/Button'
import type { Product } from './types'

function ProductStatus({ isActive }: { isActive: boolean }) {
  return (
    <Badge tone={isActive ? 'active' : 'neutral'}>
      <span
        aria-hidden='true'
        className={
          isActive ? 'size-1.5 rounded-full bg-emerald-600' : 'size-1.5 rounded-full bg-slate-500'
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
    <section
      aria-label='Listado de productos FAA'
      className='ui-panel overflow-x-auto focus-visible:ring-2 focus-visible:ring-slate-500'
    >
      <table className='w-full min-w-[38rem] border-collapse text-left text-sm'>
        <caption className='sr-only'>Productos disponibles en el CRM</caption>
        <thead>
          <tr className='border-b border-slate-200 bg-slate-50 text-xs text-slate-600'>
            <th className='px-4 py-3 font-semibold' scope='col'>
              Producto
            </th>
            <th className='px-4 py-3 font-semibold' scope='col'>
              Estado
            </th>
            {canManage ? (
              <th className='px-4 py-3 text-right font-semibold' scope='col'>
                Acciones
              </th>
            ) : null}
          </tr>
        </thead>
        <tbody>
          {products.map((product) => {
            const isBusy = busyProductIds.has(product.id)
            return (
              <tr
                className='border-b border-slate-100 last:border-b-0 hover:bg-slate-50/70'
                key={product.id}
              >
                <th className='px-4 py-3 font-semibold text-slate-950' scope='row'>
                  {product.name}
                </th>
                <td className='px-4 py-3'>
                  <ProductStatus isActive={product.is_active} />
                </td>
                {canManage ? (
                  <td className='px-4 py-3'>
                    <div className='flex min-w-max justify-end gap-2'>
                      <Button
                        aria-label={`Editar ${product.name}`}
                        disabled={isBusy}
                        onClick={() => onEdit(product)}
                        size='compact'
                      >
                        Editar
                      </Button>
                      {product.is_active ? (
                        <Button
                          aria-label={`Desactivar ${product.name}`}
                          className='text-rose-700 hover:bg-rose-50 hover:text-rose-900'
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
                  </td>
                ) : null}
              </tr>
            )
          })}
        </tbody>
      </table>
    </section>
  )
}
