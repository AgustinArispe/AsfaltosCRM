import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import {
  StageTransitionConfirmationModal,
  stageTransitionConfirmationCopy,
} from './StageTransitionConfirmationModal'

describe('StageTransitionConfirmationModal', () => {
  it('uses the approved forward, backward, and GANADA confirmation copy', () => {
    expect(stageTransitionConfirmationCopy('NUEVA', 'COTIZADA')).toEqual({
      description: '¿Querés avanzar esta oportunidad a Cotizada?',
      actionLabel: 'Avanzar a Cotizada',
    })
    expect(stageTransitionConfirmationCopy('NEGOCIACION', 'COTIZADA')).toEqual({
      description: '¿Querés volver esta oportunidad a Cotizada?',
      actionLabel: 'Volver a Cotizada',
    })
    expect(stageTransitionConfirmationCopy('NEGOCIACION', 'GANADA')).toEqual({
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
        transition={{ opportunityId: 12, fromStatus: 'NEGOCIACION', targetStatus: 'GANADA' }}
      />,
    )

    const dialog = screen.getByRole('dialog', { name: 'Confirmar cambio de etapa' })
    expect(within(dialog).getByRole('button', { name: 'Cancelar' })).toHaveFocus()
    fireEvent(dialog, new Event('cancel', { bubbles: false, cancelable: true }))
    expect(onCancel).toHaveBeenCalledTimes(1)
    fireEvent.click(within(dialog).getByRole('button', { name: 'Marcar como Ganada' }))
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })
})
