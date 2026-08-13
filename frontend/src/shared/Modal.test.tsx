import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Modal } from './Modal'

describe('Modal', () => {
  it('focuses the intended control, traps tab navigation, closes with Escape, and restores focus', () => {
    const onClose = () => rerender(<Dialog isOpen={false} onClose={onClose} />)
    const { rerender } = render(<Dialog isOpen={false} onClose={onClose} />)
    const trigger = screen.getByRole('button', { name: 'Abrir' })
    trigger.focus()

    rerender(<Dialog isOpen onClose={onClose} />)
    const dialog = screen.getByRole('dialog')
    const close = screen.getByRole('button', { name: 'Cerrar confirmar' })
    const first = screen.getByRole('button', { name: 'Primero' })
    const last = screen.getByRole('button', { name: 'Último' })
    expect(first).toHaveFocus()
    last.focus()
    fireEvent.keyDown(dialog, { key: 'Tab' })
    expect(close).toHaveFocus()
    fireEvent.keyDown(dialog, { key: 'Tab', shiftKey: true })
    expect(last).toHaveFocus()
    fireEvent.keyDown(dialog, { key: 'Escape' })
    fireEvent(dialog, new Event('cancel', { cancelable: true }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
  })
})

function Dialog({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  return (
    <>
      <button type='button'>Abrir</button>
      <Modal isOpen={isOpen} onClose={onClose} title='Confirmar'>
        <div>
          <button data-modal-initial-focus type='button'>
            Primero
          </button>
          <button type='button'>Último</button>
        </div>
      </Modal>
    </>
  )
}
