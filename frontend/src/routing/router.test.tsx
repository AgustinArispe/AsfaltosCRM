import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { AppLink, navigate, navigateRoute, navigateToHistoryOrigin } from './router'

describe('manual typed router', () => {
  it('writes typed origin state and returns to it without accepting URL strings', () => {
    navigateRoute(
      { kind: 'customer', customerId: 8 },
      { origin: { kind: 'workspace', workspace: 'whatsapp' } },
    )
    expect(window.location.pathname).toBe('/customers/8')
    expect(window.history.state).toEqual({
      crmOrigin: { kind: 'workspace', workspace: 'whatsapp' },
    })
    navigateToHistoryOrigin({ kind: 'workspace', workspace: 'customers' })
    expect(window.location.pathname).toBe('/whatsapp')

    window.history.replaceState({ crmOrigin: '/outside' }, '', '/customers/8')
    navigateToHistoryOrigin({ kind: 'workspace', workspace: 'customers' })
    expect(window.location.pathname).toBe('/customers')
  })

  it('keeps string links compatible and uses typed paths when provided', () => {
    render(
      <>
        <AppLink to='/pipeline'>Pipeline</AppLink>
        <AppLink
          origin={{ kind: 'workspace', workspace: 'customers' }}
          to={{ kind: 'customer', customerId: 9 }}
        >
          Cliente
        </AppLink>
      </>,
    )
    fireEvent.click(screen.getByRole('link', { name: 'Pipeline' }))
    expect(window.location.pathname).toBe('/pipeline')
    fireEvent.click(screen.getByRole('link', { name: 'Cliente' }))
    expect(window.location.pathname).toBe('/customers/9')
    navigate('/customers/9')
    expect(window.location.pathname).toBe('/customers/9')
  })
})
