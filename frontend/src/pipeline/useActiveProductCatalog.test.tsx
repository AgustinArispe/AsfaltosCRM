import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { useActiveProductCatalog } from './useActiveProductCatalog'

function Probe() {
  const catalog = useActiveProductCatalog({ token: 'token', onUnauthorized: vi.fn() })
  const [resultCount, setResultCount] = useState(0)
  const loadTwice = () => {
    void Promise.all([catalog.load(), catalog.load()]).then(([items]) =>
      setResultCount(items.length),
    )
  }
  return (
    <div>
      <button onClick={loadTwice} type='button'>
        Cargar dos veces
      </button>
      <button onClick={() => void catalog.load().catch(() => undefined)} type='button'>
        Cargar otra vez
      </button>
      <button onClick={() => void catalog.retry().catch(() => undefined)} type='button'>
        Reintentar
      </button>
      {catalog.error ? <span>{catalog.error}</span> : null}
      <span>{resultCount}</span>
    </div>
  )
}

describe('useActiveProductCatalog', () => {
  it('shares the in-flight request and reuses the successful mounted catalog', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([{ id: 1, name: 'CA-30', is_active: true }]), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      }),
    )
    vi.stubGlobal('fetch', fetchMock)
    render(<Probe />)
    fireEvent.click(screen.getByRole('button', { name: 'Cargar dos veces' }))
    await waitFor(() => expect(screen.getByText('1')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Cargar otra vez' }))
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('clears a failed in-flight request and retries explicitly', async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new TypeError('offline'))
      .mockResolvedValueOnce(
        new Response(JSON.stringify([{ id: 2, name: 'CA-20', is_active: true }]), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        }),
      )
    vi.stubGlobal('fetch', fetchMock)
    render(<Probe />)
    fireEvent.click(screen.getByRole('button', { name: 'Cargar otra vez' }))
    expect(
      await screen.findByText('No pudimos cargar los productos. Intentá nuevamente.'),
    ).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
  })
})
