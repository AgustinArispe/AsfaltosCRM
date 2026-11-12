import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import {
  StageTransitionConfirmationModal,
  stageTransitionConfirmationCopy,
} from './StageTransitionConfirmationModal'

describe('StageTransitionConfirmationModal', () => {
  it('uses the approved forward, backward, and GANADA confirmation copy', () => {
    expect(stageTransitionConfirmationCopy('NUEVA', 'PARA_COTIZAR')).toEqual({
      description: '¿Querés avanzar esta oportunidad a Para cotizar?',
      actionLabel: 'Avanzar a Para cotizar',
    })
    expect(stageTransitionConfirmationCopy('COTIZADA', 'PARA_COTIZAR')).toEqual({
      description: '¿Querés volver esta oportunidad a Para cotizar?',
      actionLabel: 'Volver a Para cotizar',
    })
    expect(stageTransitionConfirmationCopy('COTIZADA', 'GANADA')).toEqual({
      description: '¿Querés marcar esta oportunidad como Ganada?',
      actionLabel: 'Marcar como Ganada',
    })
  })

  it('cancels through the dialog and focuses Cancel initially', () => {
    const onCancel = vi.fn()
    const onConfirm = vi.fn()
    render(
      <StageTransitionConfirmationModal
        isPending={false}
        onCancel={onCancel}
        onConfirm={onConfirm}
        transition={{ opportunityId: 12, fromStatus: 'COTIZADA', targetStatus: 'GANADA' }}
      />,
    )

    const dialog = screen.getByRole('dialog', { name: 'Confirmar cambio de etapa' })
    expect(within(dialog).getByRole('button', { name: 'Cancelar' })).toHaveFocus()
    fireEvent(dialog, new Event('cancel', { bubbles: false, cancelable: true }))
    expect(onCancel).toHaveBeenCalledTimes(1)
    fireEvent.change(screen.getByLabelText('Nota del cambio de estado (obligatoria)'), {
      target: { value: 'Seguimiento comercial de prueba' },
    })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Marcar como Ganada' }))
    expect(onConfirm).toHaveBeenCalledTimes(1)
    expect(onConfirm).toHaveBeenCalledWith('Seguimiento comercial de prueba', undefined)
  })

  it('suggests province for a missing customer location on the pipeline win confirmation', () => {
    const onConfirm = vi.fn()
    const props = {
      isPending: false,
      onCancel: vi.fn(),
      onConfirm,
      transition: {
        opportunityId: 12,
        fromStatus: 'COTIZADA' as const,
        targetStatus: 'GANADA' as const,
      },
    }
    const { rerender } = render(
      <StageTransitionConfirmationModal {...props} customerProvince={null} />,
    )
    const province = screen.getByLabelText('Provincia (opcional, recomendada)')
    expect(province).not.toBeRequired()
    fireEvent.change(screen.getByLabelText('Nota del cambio de estado (obligatoria)'), {
      target: { value: 'Compra aprobada' },
    })
    fireEvent.change(province, { target: { value: ' Córdoba ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Marcar como Ganada' }))
    expect(onConfirm).toHaveBeenCalledWith('Compra aprobada', 'Córdoba')
    rerender(<StageTransitionConfirmationModal {...props} customerProvince='Mendoza' />)
    expect(screen.queryByLabelText('Provincia (opcional, recomendada)')).not.toBeInTheDocument()
  })
})
