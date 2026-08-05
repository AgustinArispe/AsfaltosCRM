import type { Product } from './types'

function ProductStatus({ isActive }: { isActive: boolean }) {
  return (
    <span
      className={[
        'inline-flex items-center gap-2 border px-2.5 py-1 text-xs font-bold',
        isActive
          ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
          : 'border-slate-300 bg-slate-100 text-slate-700',
      ].join(' ')}
    >
      <span
        aria-hidden="true"
        className={isActive ? 'size-1.5 bg-emerald-600' : 'size-1.5 bg-slate-500'}
      />
      {isActive ? 'Activo' : 'Inactivo'}
    </span>
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
    <div
      aria-label="Listado de productos FAA"
      className="overflow-x-auto border border-slate-200 bg-white focus-visible:ring-2 focus-visible:ring-amber-500"
      role="region"
      tabIndex={0}
    >
      <table className="w-full min-w-[38rem] border-collapse text-left text-sm">
        <caption className="sr-only">Productos disponibles en el CRM</caption>
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-600">
            <th className="px-4 py-3 font-semibold" scope="col">Producto</th>
            <th className="px-4 py-3 font-semibold" scope="col">Estado</th>
            {canManage ? (
              <th className="px-4 py-3 text-right font-semibold" scope="col">Acciones</th>
            ) : null}
          </tr>
        </thead>
        <tbody>
          {products.map((product) => {
            const isBusy = busyProductIds.has(product.id)
            return (
              <tr className="border-b border-slate-100 last:border-b-0 hover:bg-slate-50/70" key={product.id}>
                <th className="px-4 py-3 font-semibold text-slate-950" scope="row">
                  {product.name}
                </th>
                <td className="px-4 py-3"><ProductStatus isActive={product.is_active} /></td>
                {canManage ? (
                  <td className="px-4 py-3">
                    <div className="flex min-w-max justify-end gap-2">
                      <button
                        aria-label={`Editar ${product.name}`}
                        className="min-h-11 border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 outline-none hover:bg-slate-100 focus-visible:ring-2 focus-visible:ring-amber-500 disabled:cursor-not-allowed disabled:opacity-50"
                        disabled={isBusy}
                        onClick={() => onEdit(product)}
                        type="button"
                      >
                        Editar
                      </button>
                      {product.is_active ? (
                        <button
                          aria-label={`Desactivar ${product.name}`}
                          className="min-h-11 border border-red-200 px-3 py-2 text-sm font-semibold text-red-800 outline-none hover:bg-red-50 focus-visible:ring-2 focus-visible:ring-red-600 disabled:cursor-wait disabled:opacity-50"
                          disabled={isBusy}
                          onClick={() => onDeactivate(product)}
                          type="button"
                        >
                          Desactivar
                        </button>
                      ) : (
                        <button
                          aria-label={`Reactivar ${product.name}`}
                          className="min-h-11 border border-emerald-200 px-3 py-2 text-sm font-semibold text-emerald-800 outline-none hover:bg-emerald-50 focus-visible:ring-2 focus-visible:ring-emerald-600 disabled:cursor-wait disabled:opacity-50"
                          disabled={isBusy}
                          onClick={() => onReactivate(product)}
                          type="button"
                        >
                          {isBusy ? 'Reactivando…' : 'Reactivar'}
                        </button>
                      )}
                    </div>
                  </td>
                ) : null}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
