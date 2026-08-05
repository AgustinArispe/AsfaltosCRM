import type { UserRole } from '../auth/types'
import { AppLink } from '../routing/router'
import { LegendaryBadge } from './LegendaryBadge'
import { Button } from '../shared/Button'
import type { CustomerSummary } from './types'

function phoneHref(phone: string): string {
  return `tel:${phone.replace(/[^\d+]/g, '')}`
}
function MissingValue() {
  return <span className="text-slate-500">—</span>
}

export function CustomerTable({
  customers,
  role,
  onEdit,
  onDelete,
}: {
  customers: CustomerSummary[]
  role: UserRole
  onEdit: (customer: CustomerSummary) => void
  onDelete: (customer: CustomerSummary) => void
}) {
  return (
    <div
      aria-label="Listado de clientes. Desplazá horizontalmente para ver todas las columnas."
      className="ui-panel overflow-x-auto focus-visible:ring-2 focus-visible:ring-slate-500"
      role="region"
      tabIndex={0}
    >
      <table className="w-full min-w-[68rem] border-collapse text-left text-sm">
        <caption className="sr-only">Clientes activos del CRM</caption>
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50 text-xs text-slate-600">
            <th className="px-4 py-3 font-semibold" scope="col">Nombre</th>
            <th className="px-4 py-3 font-semibold" scope="col">Empresa</th>
            <th className="px-4 py-3 font-semibold" scope="col">Email</th>
            <th className="px-4 py-3 font-semibold" scope="col">Teléfono</th>
            <th className="px-4 py-3 font-semibold" scope="col">Provincia</th>
            <th className="px-4 py-3 font-semibold" scope="col">Categoría</th>
            <th className="px-4 py-3 text-right font-semibold" scope="col">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {customers.map((customer) => (
            <tr className="border-b border-slate-100 last:border-b-0 hover:bg-slate-50/70" key={customer.id}>
              <th className="px-4 py-3 font-semibold text-slate-950" scope="row">
                <AppLink
                  className="inline-flex min-h-11 items-center underline decoration-slate-300 underline-offset-4 outline-none hover:decoration-slate-700 focus-visible:ring-2 focus-visible:ring-slate-500"
                  to={`/customers/${customer.id}`}
                >
                  {customer.name}
                </AppLink>
              </th>
              <td className="max-w-52 px-4 py-3 text-slate-700">
                {customer.company ?? <MissingValue />}
              </td>
              <td className="max-w-60 px-4 py-3">
                {customer.email ? (
                  <a
                    className="break-all text-slate-700 underline decoration-slate-300 underline-offset-2 outline-none hover:text-slate-950 focus-visible:ring-2 focus-visible:ring-slate-500"
                    href={`mailto:${customer.email}`}
                  >
                    {customer.email}
                  </a>
                ) : <MissingValue />}
              </td>
              <td className="px-4 py-3">
                {customer.phone ? (
                  <a
                    className="text-slate-700 underline decoration-slate-300 underline-offset-2 outline-none hover:text-slate-950 focus-visible:ring-2 focus-visible:ring-slate-500"
                    href={phoneHref(customer.phone)}
                  >
                    {customer.phone}
                  </a>
                ) : <MissingValue />}
              </td>
              <td className="px-4 py-3 text-slate-700">
                {customer.province ?? <MissingValue />}
              </td>
              <td className="px-4 py-3">
                {customer.legendary_historical_override ? <LegendaryBadge /> : <MissingValue />}
              </td>
              <td className="px-4 py-3">
                <div className="flex min-w-max justify-end gap-2">
                  <Button
                    aria-label={`Editar a ${customer.name}`}
                    onClick={() => onEdit(customer)}
                    size="compact"
                  >
                    Editar
                  </Button>
                  {role === 'SUPERVISOR' ? (
                    <Button
                      aria-label={`Eliminar a ${customer.name}`}
                      className="text-rose-700 hover:bg-rose-50 hover:text-rose-900"
                      onClick={() => onDelete(customer)}
                      size="compact"
                      variant="ghost"
                    >
                      Eliminar
                    </Button>
                  ) : null}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
