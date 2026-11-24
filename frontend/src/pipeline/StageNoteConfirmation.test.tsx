import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { StageNoteConfirmation } from './StageNoteConfirmation'

describe('StageNoteConfirmation', () => {
  it('accepts empty notes, trims input, and preserves the note while a retryable error is visible', () => {
    const onConfirm = vi.fn()
    const props = {
      isOpen: true,
      title: 'Cambiar etapa',
      confirmLabel: 'Confirmar',
      pendingLabel: 'Guardando',
      onConfirm,
      onCancel: vi.fn(),
      children: <p>Se guardará en el cliente.</p>,
    }
    const { rerender } = render(<StageNoteConfirmation {...props} />)
    const dialog = screen.getByRole('dialog', { name: 'Cambiar etapa' })
    const confirm = within(dialog).getByRole('button', { name: 'Confirmar' })
    expect(confirm).toBeEnabled()
    const input = within(dialog).getByLabelText('Nota del cambio de estado (recomendada)')
    expect(input).not.toBeRequired()
    expect(input).toHaveAttribute('maxLength', '4000')
    fireEvent.change(input, { target: { value: '   ' } })
    expect(confirm).toBeEnabled()
    fireEvent.click(confirm)
    expect(onConfirm).toHaveBeenLastCalledWith('', undefined, undefined)
    fireEvent.change(input, { target: { value: '  Cliente contactado  ' } })
    fireEvent.click(confirm)
    expect(onConfirm).toHaveBeenCalledWith('Cliente contactado', undefined, undefined)
    rerender(<StageNoteConfirmation {...props} error='No se pudo guardar' />)
    expect(input).toHaveValue('  Cliente contactado  ')
    expect(screen.getByRole('alert')).toHaveTextContent('No se pudo guardar')
    rerender(<StageNoteConfirmation {...props} isOpen={false} />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    rerender(<StageNoteConfirmation {...props} />)
    expect(screen.getByLabelText('Nota del cambio de estado (recomendada)')).toHaveValue('')
  })

  it('recommends province without requiring it and preserves the draft after an error', () => {
    const onConfirm = vi.fn()
    const props = {
      isOpen: true,
      title: 'Ganada',
      confirmLabel: 'Confirmar',
      pendingLabel: 'Guardando',
      onConfirm,
      onCancel: vi.fn(),
      suggestProvince: true,
      children: <p>Confirmá la venta.</p>,
    }
    const { rerender } = render(<StageNoteConfirmation {...props} />)
    const province = screen.getByLabelText('Provincia (opcional, recomendada)')
    expect(province).not.toBeRequired()
    fireEvent.change(screen.getByLabelText('Nota del cambio de estado (recomendada)'), {
      target: { value: 'Cliente confirmó' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar' }))
    expect(onConfirm).toHaveBeenLastCalledWith('Cliente confirmó', undefined, undefined)
    fireEvent.change(province, { target: { value: ' Córdoba ' } })
    rerender(<StageNoteConfirmation {...props} error='Reintentar' />)
    expect(province).toHaveValue(' Córdoba ')
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar' }))
    expect(onConfirm).toHaveBeenLastCalledWith('Cliente confirmó', 'Córdoba', undefined)
    rerender(<StageNoteConfirmation {...props} isPending />)
    expect(province).toBeDisabled()
    rerender(<StageNoteConfirmation {...props} isOpen={false} />)
    rerender(<StageNoteConfirmation {...props} />)
    expect(screen.getByLabelText('Provincia (opcional, recomendada)')).toHaveValue('')
  })
})
