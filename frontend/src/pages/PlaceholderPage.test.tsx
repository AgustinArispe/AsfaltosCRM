import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { PlaceholderPage } from './PlaceholderPage'

describe('PlaceholderPage', () => {
  it('keeps unavailable workspace feedback clear and scoped', () => {
    render(<PlaceholderPage description='Disponible más adelante.' title='Métricas' />)
    expect(screen.getByText('Métricas')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Métricas' })).toBeInTheDocument()
    expect(screen.getByText('Disponible más adelante.')).toBeInTheDocument()
  })
})
