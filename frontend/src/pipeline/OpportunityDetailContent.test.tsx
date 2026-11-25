import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { OpportunityContextPanel } from './OpportunityContextPanel'
import { OpportunityDetailContent, OpportunityDetailModalHeader } from './OpportunityDetailContent'
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
  loss_reason: 'OTRO',
  loss_reason_detail: 'El cliente cambió el alcance del proyecto.',
  loss_events: [
    {
      id: 3,
      status_history_id: 2,
      reason: 'OTRO',
      loss_reason_detail: 'El cliente cambió el alcance del proyecto.',
      lost_at: '2026-08-01T12:00:00Z',
    },
  ],
  updated_at: '2026-08-01T12:00:00Z',
  web_intake: null,
}

describe('OpportunityDetailContent', () => {
  it('shows transition notes in the activity panel used by the opportunity drawer', () => {
    render(
      <OpportunityContextPanel
        opportunity={{
          ...opportunity,
          history: [
            {
              id: 4,
              from_status: 'PARA_COTIZAR',
              to_status: 'COTIZADA',
              changed_at: '2026-11-11T12:00:00Z',
              changed_by_user_id: 2,
              note: 'Se envió la cotización.\nEl cliente la está revisando.',
            },
          ],
        }}
        session={{ token: 'local-test', onUnauthorized: () => undefined }}
      />,
    )

    expect(screen.getByText('Pasó de Para cotizar a Cotizada')).toBeInTheDocument()
    expect(screen.getByText(/Se envió la cotización/)).toHaveTextContent(
      'Se envió la cotización. El cliente la está revisando.',
    )
    expect(screen.getByText(/Se envió la cotización/)).toHaveClass('whitespace-pre-wrap')
  })

  it('renders the commercial detail, loss context, customer contacts, quote and history', () => {
    render(
      <>
        <OpportunityDetailModalHeader
          opportunity={opportunity}
          returnAffordance={<a href='/pipeline'>Volver al Pipeline</a>}
          titleId='opportunity-title'
        />
        <OpportunityDetailContent
          actions={<button type='button'>Acción</button>}
          opportunity={opportunity}
        />
      </>,
    )
    expect(screen.getByRole('heading', { name: 'FAA Construcciones' })).toBeInTheDocument()
    expect(screen.getByText('Legendario')).toBeInTheDocument()
    expect(screen.getByText('Motivo de pérdida')).toBeInTheDocument()
    expect(screen.getAllByText('El cliente cambió el alcance del proyecto.')).toHaveLength(2)
    expect(screen.getByRole('link', { name: 'carla@faa.test' })).toHaveAttribute(
      'href',
      'mailto:carla@faa.test',
    )
    expect(screen.getByRole('link', { name: '+54 11 5555 0101' })).toHaveAttribute(
      'href',
      'tel:+54 11 5555 0101',
    )
    expect(screen.getByRole('button', { name: 'Actividad y notas' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(screen.getByText('Pasó de Negociación (histórico) a Pérdida')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Cotización' }))
    expect(screen.getByText('Producto histórico')).toBeInTheDocument()
    expect(screen.getByText('Inactivo')).toBeInTheDocument()
    expect(screen.getByText('Total cotizado')).toBeInTheDocument()
    expect(screen.getByText('Consulta creada')).toBeInTheDocument()
    expect(screen.getByText('Pasó de Negociación (histórico) a Pérdida')).toBeInTheDocument()

    const summary = document.querySelector('.opportunity-detail__summary--page')
    expect(summary).not.toBeNull()
    expect(
      Array.from(summary?.querySelectorAll('dt') ?? []).map((term) => term.textContent),
    ).toEqual(['Origen', 'Responsable', 'Email', 'Teléfono', 'Provincia'])
    expect(
      screen.queryByRole('heading', { name: 'Información del cliente' }),
    ).not.toBeInTheDocument()
    expect(document.querySelector('.opportunity-detail__body--page')).not.toBeNull()
    expect(screen.queryByRole('region', { name: 'Historial' })).not.toBeInTheDocument()
  })

  it('renders missing customer information and the no-quote state in compact layout', () => {
    render(
      <OpportunityDetailContent
        layout='drawer'
        opportunity={{
          ...opportunity,
          status: 'NUEVA',
          loss_reason: null,
          loss_reason_detail: null,
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
    expect(screen.getByRole('heading', { name: 'Información del cliente' })).toBeInTheDocument()
  })

  it('opens the customer inquiry first before quoting and prioritizes the quote after the stage changes', () => {
    const detail: OpportunityDetail = {
      ...opportunity,
      status: 'PARA_COTIZAR',
      source: 'WEB',
      web_intake: { message: 'Primera línea\nSegunda línea' },
    }
    const { rerender } = render(<OpportunityDetailContent opportunity={detail} />)
    const sections = screen.getByRole('group', { name: 'Secciones de la oportunidad' })
    const consultation = within(sections).getByRole('button', { name: 'Consulta del cliente' })
    expect(consultation).toHaveAttribute('aria-pressed', 'true')
    const message = screen.getByText(/Primera línea/)
    expect(message).toBeVisible()
    expect(message).toHaveTextContent('Primera línea Segunda línea')
    expect(message).toHaveClass('whitespace-pre-wrap', 'break-words', '[overflow-wrap:anywhere]')
    expect(screen.queryByRole('region', { name: 'Cotización' })).not.toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Historial' })).not.toBeInTheDocument()

    rerender(<OpportunityDetailContent opportunity={{ ...detail, status: 'COTIZADA' }} />)
    expect(within(sections).getAllByRole('button')[0]).toHaveAccessibleName('Cotización')
    expect(screen.getByRole('region', { name: 'Cotización' })).toBeVisible()
    fireEvent.click(consultation)
    expect(screen.getByText(/Primera línea/)).toBeVisible()
    expect(screen.queryByRole('region', { name: 'Cotización' })).not.toBeInTheDocument()
  })

  it('opens activity first when a new web lead has no inquiry to show', () => {
    render(
      <OpportunityDetailContent
        opportunity={{
          ...opportunity,
          status: 'NUEVA',
          source: 'WEB',
          web_intake: { message: null },
        }}
      />,
    )

    const sections = screen.getByRole('group', { name: 'Secciones de la oportunidad' })
    expect(within(sections).getAllByRole('button')).toHaveLength(2)
    expect(within(sections).getByRole('button', { name: 'Actividad y notas' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(screen.getByRole('region', { name: 'Historial' })).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Consulta del cliente' })).not.toBeInTheDocument()
  })

  it('does not render the web consultation for a WhatsApp opportunity', () => {
    render(<OpportunityDetailContent opportunity={opportunity} />)

    expect(screen.queryByRole('heading', { name: 'Consulta del cliente' })).not.toBeInTheDocument()
  })
})
