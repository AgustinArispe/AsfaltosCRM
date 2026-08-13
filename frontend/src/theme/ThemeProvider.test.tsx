import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ThemeProvider, useTheme } from './ThemeProvider'

const listeners = new Set<(event: MediaQueryListEvent) => void>()
let prefersDark = false

function ThemeProbe() {
  const { preference, resolvedTheme, setPreference } = useTheme()
  return (
    <>
      <p>{`${preference}/${resolvedTheme}`}</p>
      <button onClick={() => setPreference('light')} type='button'>
        Claro
      </button>
      <button onClick={() => setPreference('dark')} type='button'>
        Oscuro
      </button>
      <button onClick={() => setPreference('system')} type='button'>
        Sistema
      </button>
    </>
  )
}

describe('ThemeProvider', () => {
  beforeEach(() => {
    prefersDark = false
    listeners.clear()
    vi.stubGlobal('matchMedia', (query: string) => ({
      media: query,
      matches: prefersDark,
      addEventListener: (_: string, listener: (event: MediaQueryListEvent) => void) =>
        listeners.add(listener),
      removeEventListener: (_: string, listener: (event: MediaQueryListEvent) => void) =>
        listeners.delete(listener),
    }))
  })

  it('uses system by default, persists an explicit choice, and applies semantic theme state', () => {
    prefersDark = true
    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    )

    expect(screen.getByText('system/dark')).toBeInTheDocument()
    expect(document.documentElement.dataset.theme).toBe('dark')
    fireEvent.click(screen.getByRole('button', { name: 'Claro' }))
    expect(screen.getByText('light/light')).toBeInTheDocument()
    expect(window.localStorage.getItem('faa-crm.theme')).toBe('light')
    expect(document.documentElement.style.colorScheme).toBe('light')
  })

  it('follows an operating-system change when system is selected', async () => {
    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Oscuro' }))
    fireEvent.click(screen.getByRole('button', { name: 'Sistema' }))
    await waitFor(() => expect(listeners.size).toBeGreaterThan(0))
    prefersDark = true
    act(() => {
      for (const listener of listeners) listener({ matches: true } as MediaQueryListEvent)
    })

    expect(screen.getByText('system/dark')).toBeInTheDocument()
    expect(window.localStorage.getItem('faa-crm.theme')).toBeNull()
  })
})
