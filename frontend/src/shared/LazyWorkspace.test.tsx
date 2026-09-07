import { render, screen } from '@testing-library/react'
import { Component, type ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LazyWorkspace } from './LazyWorkspace'

class ThrowingChild extends Component<{ children?: ReactNode }> {
  render(): ReactNode {
    throw new Error('chunk failed')
  }
}

describe('LazyWorkspace', () => {
  beforeEach(() => vi.spyOn(console, 'error').mockImplementation(() => undefined))

  it('keeps chunk failures safe and recoverable', () => {
    render(
      <LazyWorkspace>
        <ThrowingChild />
      </LazyWorkspace>,
    )
    expect(screen.getByRole('alert')).toHaveTextContent('No pudimos cargar esta sección')
    expect(screen.getByRole('button', { name: 'Reintentar' })).toBeInTheDocument()
  })

  it('renders an available workspace normally', () => {
    render(
      <LazyWorkspace>
        <p>Contenido disponible</p>
      </LazyWorkspace>,
    )
    expect(screen.getByText('Contenido disponible')).toBeInTheDocument()
  })
})
