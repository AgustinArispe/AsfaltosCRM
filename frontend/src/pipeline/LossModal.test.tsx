import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { LossModal } from './LossModal'
import type { OpportunitySummary } from './types'

const opportunity: OpportunitySummary = {
  id: 1,
  status: 'NUEVA',
  source: 'WEB',
  current_status_entered_at: '2026-08-01T12:00:00Z',
  customer: {
    id: 1,
    name: 'Cliente',
    company: null,
    email: null,
    phone: null,
    province: null,
    legendary_historical_override: false,
  },
  assigned_user: null,
  products: [],
  created_at: '2026-08-01T12:00:00Z',
}

describe('LossModal', () => {
  it('requires a reason and submits a selected loss reason', async () => {
    const onConfirm = vi.fn(async () => undefined)
    render(<LossModal onClose={vi.fn()} onConfirm={onConfirm} opportunity={opportunity} />)
    const dialog = screen.getByRole('dialog', { name: 'Marcar como perdida' })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Confirmar pérdida' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Seleccioná un motivo')
    fireEvent.change(within(dialog).getByLabelText('Motivo'), { target: { value: 'PRECIO' } })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Confirmar pérdida' }))
    await waitFor(() => expect(onConfirm).toHaveBeenCalledWith('PRECIO'))
  })

  it('keeps the dialog open with a useful command error', async () => {
    render(
      <LossModal
        onClose={vi.fn()}
        onConfirm={async () => {
          throw new Error('No disponible')
        }}
        opportunity={opportunity}
      />,
    )
    fireEvent.change(screen.getByLabelText('Motivo'), { target: { value: 'OTRO' } })
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar pérdida' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('No disponible')
  })

  it('uses the generic error when the rejected value is not an Error', async () => {
    render(
      <LossModal
        onClose={vi.fn()}
        onConfirm={async () => Promise.reject('unexpected')}
        opportunity={opportunity}
      />,
    )
    fireEvent.change(screen.getByLabelText('Motivo'), { target: { value: 'OTRO' } })
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar pérdida' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No pudimos marcar la oportunidad como perdida.',
    )
  })
})
