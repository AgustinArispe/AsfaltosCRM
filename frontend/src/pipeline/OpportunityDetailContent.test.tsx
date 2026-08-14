import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { OpportunityDetailContent } from './OpportunityDetailContent'
import type { OpportunityDetail } from './types'

const opportunity: OpportunityDetail = {
  id: 9,
  status: 'PERDIDA',
  source: 'WHATSAPP',
  current_status_entered_at: '2026-08-01T12:00:00Z',
  customer: {
    id: 7,
    name: 'Carla Cliente',
    company: 'FAA Construcciones',
    email: 'carla@faa.test',
    phone: '+54 11 5555 0101',
    province: 'Buenos Aires',
    legendary_historical_override: true,
  },
  assigned_user: null,
  products: [
    {
      product: { id: 4, name: 'Producto histórico', is_active: false },
      quantity_kg: '2500.000',
    },
  ],
  created_at: '2026-07-01T12:00:00Z',
  history: [
    {
      id: 1,
      from_status: null,
      to_status: 'NUEVA',
      changed_at: '2026-07-01T12:00:00Z',
      changed_by_user_id: null,
    },
    {
      id: 2,
      from_status: 'NEGOCIACION',
      to_status: 'PERDIDA',
      changed_at: '2026-08-01T12:00:00Z',
      changed_by_user_id: 2,
    },
  ],
  loss_reason: 'PRECIO',
  updated_at: '2026-08-01T12:00:00Z',
}

describe('OpportunityDetailContent', () => {
  it('renders the commercial detail, loss context, customer contacts, quote and history', () => {
    render(
      <OpportunityDetailContent
        actions={<button type='button'>Acción</button>}
        opportunity={opportunity}
      />,
    )
    expect(screen.getByRole('heading', { name: 'FAA Construcciones' })).toBeInTheDocument()
    expect(screen.getByText('Legendario')).toBeInTheDocument()
    expect(screen.getByText('Motivo de pérdida')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'carla@faa.test' })).toHaveAttribute(
      'href',
      'mailto:carla@faa.test',
    )
    expect(screen.getByRole('link', { name: '+54 11 5555 0101' })).toHaveAttribute(
      'href',
      'tel:+54 11 5555 0101',
    )
    expect(screen.getByText('Producto histórico')).toBeInTheDocument()
    expect(screen.getByText('Inactivo')).toBeInTheDocument()
    expect(screen.getByText('Total cotizado')).toBeInTheDocument()
    expect(screen.getByText('Consulta creada')).toBeInTheDocument()
    expect(screen.getByText(/Pasó de Negociación a Perdida/)).toBeInTheDocument()
  })

  it('renders missing customer information and the no-quote state in compact layout', () => {
    render(
      <OpportunityDetailContent
        layout='drawer'
        opportunity={{
          ...opportunity,
          status: 'NUEVA',
          loss_reason: null,
          products: [],
          customer: {
            ...opportunity.customer,
            company: null,
            email: null,
            phone: null,
            province: null,
            legendary_historical_override: false,
          },
          history: [],
        }}
      />,
    )
    expect(screen.getAllByText('No informado')).toHaveLength(2)
    expect(screen.getByText('No informada')).toBeInTheDocument()
    expect(screen.getByText('Aún no se registró una cotización.')).toBeInTheDocument()
  })
})
