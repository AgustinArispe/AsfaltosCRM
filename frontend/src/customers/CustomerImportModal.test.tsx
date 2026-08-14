import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { CustomerImportModal } from './CustomerImportModal'

const session = { token: 'token', onUnauthorized: vi.fn() }
const validReport = {
  id: 7,
  client_import_id: '11111111-1111-4111-8111-111111111111',
  file_sha256: 'a'.repeat(64),
  source_filename: 'clientes.csv',
  status: 'VALID' as const,
  version: 1,
  row_count: 1,
  create_count: 1,
  enrich_count: 0,
  unchanged_count: 0,
  error_count: 0,
  rows: [],
  created_at: '2026-08-14T12:00:00Z',
  committed_at: null,
}

function response(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function selectCsv(): void {
  fireEvent.change(screen.getByLabelText('Archivo CSV'), {
    target: { files: [new File(['name\nCliente'], 'clientes.csv', { type: 'text/csv' })] },
  })
}

describe('CustomerImportModal', () => {
  it('keeps selection context and reports a missing file without committing', async () => {
    render(<CustomerImportModal isOpen onClose={vi.fn()} onCommitted={vi.fn()} session={session} />)
    fireEvent.click(screen.getByRole('button', { name: 'Validar archivo' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Elegí un archivo CSV')
  })

  it('requires an explicit discard before closing a selected import', async () => {
    const onClose = vi.fn()
    render(<CustomerImportModal isOpen onClose={onClose} onCommitted={vi.fn()} session={session} />)
    selectCsv()

    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('importación en curso')
    expect(onClose).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Descartar importación' }))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('shows typed validation issues and never offers commit for an invalid preview', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        response(201, {
          ...validReport,
          status: 'INVALID',
          error_count: 1,
          create_count: 0,
          rows: [
            {
              row_number: 2,
              name: '',
              company: null,
              email: null,
              phone: null,
              province: null,
              action: 'ERROR',
              resolved_customer_id: null,
              issues: [{ field_name: 'name', code: 'MISSING_NAME', message: 'Falta el nombre' }],
            },
          ],
        }),
      ),
    )
    render(<CustomerImportModal isOpen onClose={vi.fn()} onCommitted={vi.fn()} session={session} />)
    selectCsv()
    fireEvent.click(screen.getByRole('button', { name: 'Validar archivo' }))
    expect(await screen.findByText('Fila 2')).toBeInTheDocument()
    expect(screen.getByText(/name:.*Falta/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Confirmar importación' })).not.toBeInTheDocument()
  })

  it('reconciles an ambiguous commit through the persisted committed report', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = new URL(String(input), 'http://localhost')
        if (url.pathname.endsWith('/dry-run')) return response(201, validReport)
        if (url.pathname.endsWith('/commit') && init?.method === 'POST')
          return response(503, { detail: 'unavailable' })
        return response(200, {
          ...validReport,
          status: 'COMMITTED',
          committed_at: '2026-08-14T12:01:00Z',
        })
      }),
    )
    const onCommitted = vi.fn()
    render(
      <CustomerImportModal isOpen onClose={vi.fn()} onCommitted={onCommitted} session={session} />,
    )
    selectCsv()
    fireEvent.click(screen.getByRole('button', { name: 'Validar archivo' }))
    const review = await screen.findByRole('dialog', { name: 'Revisar importación' })
    fireEvent.click(within(review).getByRole('button', { name: 'Confirmar importación' }))
    expect(
      await screen.findByRole('dialog', { name: 'Importación completada' }),
    ).toBeInTheDocument()
    expect(onCommitted).toHaveBeenCalledOnce()
  })
})
