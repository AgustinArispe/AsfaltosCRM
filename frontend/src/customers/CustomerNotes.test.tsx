import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { CustomerNotes } from './CustomerNotes'
import type { CustomerNote } from './types'

const session = { token: 'customer-notes-test', onUnauthorized: vi.fn() }
const first: CustomerNote = {
  id: 1,
  body: 'Prefiere cotizaciones por escrito',
  pinned: false,
  author_name: 'Vendedora FAA',
  created_at: '2026-11-24T16:00:00Z',
  updated_at: '2026-11-24T16:00:00Z',
}

describe('CustomerNotes', () => {
  it('adds a note in WhatsApp and makes it available for editing and pinning in the sheet', async () => {
    let notes: CustomerNote[] = [first]
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), 'http://localhost')
      const path = '/api/customers/7/notes'
      if (url.pathname === path && init?.method === 'POST') {
        const body = JSON.parse(String(init.body)) as { body: string; command_id: string }
        expect(body.command_id).toBeTruthy()
        const created = { ...first, id: 2, body: body.body }
        notes = [created, ...notes]
        return Response.json(created, { status: 201 })
      }
      if (url.pathname === `${path}/2` && init?.method === 'PUT') {
        const body = JSON.parse(String(init.body)) as { body: string; pinned: boolean }
        const updated = { ...notes[0], body: body.body, pinned: body.pinned }
        notes = [updated, ...notes.slice(1)]
        return Response.json(updated)
      }
      if (url.pathname === `${path}/2` && init?.method === 'DELETE') {
        notes = notes.filter((note) => note.id !== 2)
        return new Response(null, { status: 204 })
      }
      if (url.pathname === path) {
        return Response.json({ items: notes, total: notes.length, page: 1, page_size: 10 })
      }
      throw new Error(`Unexpected request ${url.pathname}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const { rerender } = render(<CustomerNotes compact customerId={7} session={session} />)
    expect(await screen.findByText(first.body)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Agregar nota del cliente' }))
    expect(screen.getByRole('button', { name: 'Guardar nota' })).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Nota del cliente'), {
      target: { value: '  Prefiere mensajes por la tarde  ' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar nota' }))
    expect(
      await screen.findByText('Prefiere mensajes por la tarde', { selector: 'p' }),
    ).toBeInTheDocument()
    rerender(<CustomerNotes customerId={7} session={session} />)

    const noteRow = screen
      .getAllByRole('listitem')
      .find((item) => item.textContent?.includes('Prefiere mensajes por la tarde'))
    if (!noteRow) throw new Error('Missing customer note')
    fireEvent.click(within(noteRow).getByRole('button', { name: 'Editar nota' }))
    fireEvent.change(screen.getByLabelText('Nota del cliente'), {
      target: { value: 'Prefiere mensajes después de las 15' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar nota' }))
    expect(
      await screen.findByText('Prefiere mensajes después de las 15', { selector: 'p' }),
    ).toBeInTheDocument()
    fireEvent.click(within(noteRow).getByRole('button', { name: 'Fijar' }))
    expect(await within(noteRow).findByRole('button', { name: 'Desfijar' })).toBeInTheDocument()
    fireEvent.click(within(noteRow).getByRole('button', { name: 'Archivar' }))
    const dialog = screen.getByRole('dialog', { name: 'Archivar nota del cliente' })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Archivar nota' }))
    expect(await screen.findByText(first.body)).toBeInTheDocument()
    await vi.waitFor(() =>
      expect(screen.queryByText('Prefiere mensajes después de las 15')).not.toBeInTheDocument(),
    )
  })
})
