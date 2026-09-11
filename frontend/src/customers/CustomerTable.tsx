import type { UserRole } from '../auth/types'
import { AppLink } from '../routing/router'
import { Button } from '../shared/Button'
import { Icon } from '../shared/Icon'
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
    <section aria-label='Listado de clientes' className='customer-records'>
      <ul className='workspace-record-list'>
        {customers.map((customer) => (
          <li className='workspace-record-card customer-record' key={customer.id}>
            <AppLink
              aria-label={customer.name}
              className='customer-record__main'
              origin={{ kind: 'workspace', workspace: 'customers' }}
              to={{ kind: 'customer', customerId: customer.id }}
            >
              <span className='workspace-record-icon'>
                <Icon name='users' />
              </span>
              <span className='workspace-record-identity customer-record__identity'>
                <strong>{customer.name}</strong>
                {customer.company ? <span>{customer.company}</span> : null}
                {customer.is_legendary || customer.legendary_historical_override ? (
                  <LegendaryBadge />
                ) : null}
              </span>
              <span className='customer-record__province'>
                <Icon name='map-pin' />
                {customer.province ?? 'Sin provincia'}
              </span>
              <Icon className='workspace-record-chevron' name='chevron-right' />
            </AppLink>
            <span className='customer-record__contact'>
              <small>Contacto</small>
              {customer.email ? (
                <a href={`mailto:${customer.email}`}>{customer.email}</a>
              ) : customer.phone ? (
                <a href={phoneHref(customer.phone)}>{customer.phone}</a>
              ) : (
                <MissingValue />
              )}
            </span>
            <div className='workspace-record-actions customer-record__actions'>
              <Button
                aria-label={`Editar a ${customer.name}`}
                onClick={() => onEdit(customer)}
                size='compact'
                variant='ghost'
              >
                <Icon name='pencil' />
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
          </li>
        ))}
      </ul>
    </section>
  )
}
