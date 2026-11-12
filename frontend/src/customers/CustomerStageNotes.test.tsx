import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { CustomerStageNotes } from './CustomerStageNotes'

const session = { token: 'local-test', onUnauthorized: vi.fn() }
const item = {
  id: 1,
  opportunity_id: 42,
  from_status: 'NUEVA',
  to_status: 'PARA_COTIZAR',
  changed_at: '2026-11-11T15:00:00Z',
  changed_by_user_id: 1,
  author_name: 'Supervisora FAA',
  note: 'Preparar la propuesta con las cantidades solicitadas.',
}
function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('CustomerStageNotes', () => {
  it('shows the note with author, stage, date and opportunity and pages through bounded results', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(response({ items: [item], total: 21, page: 1, page_size: 20 }))
      .mockResolvedValueOnce(
        response({
          items: [{ ...item, id: 2, note: 'Segunda página' }],
          total: 21,
          page: 2,
          page_size: 20,
        }),
      )
    vi.stubGlobal('fetch', fetchMock)
    render(<CustomerStageNotes customerId={7} session={session} />)
    expect(await screen.findByText(item.note)).toBeVisible()
    expect(screen.getByText(/Nueva → Para cotizar · Supervisora FAA/)).toBeVisible()
    expect(screen.getByRole('link', { name: 'Ver oportunidad #42' })).toHaveAttribute(
      'href',
      '/pipeline/opportunities/42',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(await screen.findByText('Segunda página')).toBeVisible()
    expect(String(fetchMock.mock.calls[1][0])).toContain(
      '/customers/7/stage-notes?page=2&page_size=20',
    )
  })

  it('has a retryable local error and an honest empty state', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockRejectedValueOnce(new Error('network'))
        .mockResolvedValueOnce(response({ items: [], total: 0, page: 1, page_size: 20 })),
    )
    render(<CustomerStageNotes customerId={7} session={session} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('No pudimos cargar las notas')
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(
      await screen.findByText('Todavía no hay notas de cambios de estado para este cliente.'),
    ).toBeVisible()
  })

  it('does not show a previous customer request after unmounting', async () => {
    let resolve: ((value: Response) => void) | undefined
    vi.stubGlobal(
      'fetch',
      vi.fn(
        () =>
          new Promise<Response>((done) => {
            resolve = done
          }),
      ),
    )
    const { unmount } = render(<CustomerStageNotes customerId={7} session={session} />)
    unmount()
    resolve?.(response({ items: [item], total: 1, page: 1, page_size: 20 }))
    await waitFor(() => expect(screen.queryByText(item.note)).not.toBeInTheDocument())
  })
})
