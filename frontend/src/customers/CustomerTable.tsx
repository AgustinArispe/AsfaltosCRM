import type { UserRole } from '../auth/types'
import { AppLink } from '../routing/router'
import { Button } from '../shared/Button'
import { LegendaryBadge } from './LegendaryBadge'
import type { CustomerSummary } from './types'

function phoneHref(phone: string): string {
  return `tel:${phone.replace(/[^\d+]/g, '')}`
}
function MissingValue() {
  return <span className='text-[var(--text-tertiary)]'>—</span>
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
    <section
      aria-label='Listado de clientes'
      className='ui-panel overflow-x-auto focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]'
    >
      <table className='w-full min-w-[42rem] border-collapse text-left text-sm'>
        <caption className='sr-only'>Clientes activos del CRM</caption>
        <thead>
          <tr className='border-b border-[var(--subtle-border)] bg-[var(--surface-interactive)] text-xs text-[var(--text-secondary)]'>
            <th className='px-4 py-3 font-semibold' scope='col'>
              Nombre
            </th>
            <th className='px-4 py-3 font-semibold' scope='col'>
              <span className='sr-only'>Identidad</span>
            </th>
            <th className='hidden px-4 py-3 font-semibold lg:table-cell' scope='col'>
              Provincia
            </th>
            <th className='px-4 py-3 font-semibold' scope='col'>
              Categoría
            </th>
            <th className='px-4 py-3 text-right font-semibold' scope='col'>
              Acciones
            </th>
          </tr>
        </thead>
        <tbody>
          {customers.map((customer) => (
            <tr
              className='border-b border-[var(--border-subtle)] last:border-b-0 hover:bg-[var(--hover)]'
              key={customer.id}
            >
              <th className='px-4 py-3 font-semibold text-[var(--text-primary)]' scope='row'>
                <AppLink
                  aria-label={customer.name}
                  className='inline-flex min-h-11 items-center outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]'
                  origin={{ kind: 'workspace', workspace: 'customers' }}
                  to={{ kind: 'customer', customerId: customer.id }}
                >
                  <span>
                    {customer.name}
                    {customer.company ? (
                      <span className='mt-0.5 block font-normal text-[var(--text-secondary)]'>
                        {customer.company}
                      </span>
                    ) : null}
                  </span>
                </AppLink>
              </th>
              <td className='px-4 py-3'>
                {customer.email ? (
                  <a
                    className='break-all text-[var(--text-secondary)] underline decoration-[var(--border-strong)] underline-offset-2 outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]'
                    href={`mailto:${customer.email}`}
                  >
                    {customer.email}
                  </a>
                ) : customer.phone ? (
                  <a
                    className='text-[var(--text-secondary)] underline decoration-[var(--border-strong)] underline-offset-2 outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]'
                    href={phoneHref(customer.phone)}
                  >
                    {customer.phone}
                  </a>
                ) : (
                  <MissingValue />
                )}
              </td>
              <td className='hidden px-4 py-3 text-[var(--text-secondary)] lg:table-cell'>
                {customer.province ?? <MissingValue />}
              </td>
              <td className='px-4 py-3'>
                {customer.is_legendary || customer.legendary_historical_override ? (
                  <LegendaryBadge />
                ) : (
                  <MissingValue />
                )}
              </td>
              <td className='px-4 py-3'>
                <div className='flex min-w-max justify-end gap-2'>
                  <Button
                    aria-label={`Editar a ${customer.name}`}
                    onClick={() => onEdit(customer)}
                    size='compact'
                  >
                    Editar
                  </Button>
                  {role === 'SUPERVISOR' ? (
                    <Button
                      aria-label={`Eliminar a ${customer.name}`}
                      className='text-[var(--destructive-text)] hover:bg-[var(--destructive-subtle)] hover:text-[var(--destructive-text)]'
                      onClick={() => onDelete(customer)}
                      size='compact'
                      variant='ghost'
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
    </section>
  )
}
