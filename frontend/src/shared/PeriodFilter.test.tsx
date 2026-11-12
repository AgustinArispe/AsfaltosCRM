import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { PeriodFilter } from './PeriodFilter'

describe('PeriodFilter', () => {
  it('exposes the 15-day quick range and rejects incomplete/inverted manual drafts', () => {
    const onChange = vi.fn()
    render(<PeriodFilter value={{ preset: 'all', from: '', to: '' }} onChange={onChange} />)
    expect(screen.getByRole('combobox', { name: 'Más períodos' })).toHaveAttribute(
      'aria-label',
      'Más períodos',
    )
    expect(screen.getByRole('button', { name: 'Todo', pressed: true })).toBeVisible()
    fireEvent.change(screen.getByLabelText('Desde'), { target: { value: '2026-11-10' } })
    expect(onChange).not.toHaveBeenCalled()
    fireEvent.change(screen.getByLabelText('Hasta'), { target: { value: '2026-11-09' } })
    expect(onChange).not.toHaveBeenCalled()
    expect(screen.getByRole('status')).toHaveTextContent('Hasta debe ser igual o posterior')
    fireEvent.change(screen.getByLabelText('Hasta'), { target: { value: '2026-11-11' } })
    expect(onChange).toHaveBeenLastCalledWith({
      preset: 'custom',
      from: '2026-11-10',
      to: '2026-11-11',
    })
    fireEvent.click(screen.getByRole('button', { name: 'Últimos 15 días' }))
    expect(onChange.mock.lastCall?.[0].preset).toBe('last-15-days')
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Todo' }))
    expect(screen.getByLabelText('Desde')).toHaveValue('')
    expect(screen.getByLabelText('Hasta')).toHaveValue('')
  })
})
