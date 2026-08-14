import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { ComponentProps } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { HumanTemplateSelector } from './HumanTemplateSelector'
import type { HumanTemplateSendInput, WhatsAppHumanTemplate } from './types'

const documentTemplate: WhatsAppHumanTemplate = {
  name: 'ficha_tecnica',
  language: 'es_AR',
  category: 'UTILITY',
  parameter_names: ['obra'],
  header_type: 'DOCUMENT',
  header_media_required: true,
  body_preview: null,
}

function renderSelector(overrides: Partial<ComponentProps<typeof HumanTemplateSelector>> = {}) {
  const onClose = vi.fn()
  const onReload = vi.fn(async () => undefined)
  const onSend = vi.fn(async (_input: HumanTemplateSendInput) => true)
  render(
    <HumanTemplateSelector
      error={null}
      isOpen
      isSending={false}
      onClose={onClose}
      onReload={onReload}
      onSend={onSend}
      status='ready'
      templates={[documentTemplate]}
      {...overrides}
    />,
  )
  return { onClose, onReload, onSend }
}

describe('HumanTemplateSelector', () => {
  beforeEach(() => {
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      value: vi.fn(() => 'blob:http://localhost/template-header'),
    })
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: vi.fn() })
  })

  it('sends only the selected safe template requirements and opaque PDF attachment', async () => {
    const { onClose, onReload, onSend } = renderSelector()
    await waitFor(() => expect(onReload).toHaveBeenCalledTimes(1))

    fireEvent.click(screen.getByRole('button', { name: /ficha_tecnica/i }))
    expect(
      screen.getByText('El contenido se administra en la plantilla aprobada.'),
    ).toBeInTheDocument()
    fireEvent.change(screen.getByRole('textbox', { name: 'obra' }), {
      target: { value: 'Planta Norte' },
    })
    fireEvent.change(screen.getByLabelText('Adjuntar PDF'), {
      target: { files: [new File(['pdf'], 'ficha.pdf', { type: 'application/pdf' })] },
    })
    expect(screen.getByText('ficha.pdf')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Enviar plantilla' }))

    await waitFor(() => expect(onSend).toHaveBeenCalledTimes(1))
    expect(onSend).toHaveBeenCalledWith(
      expect.objectContaining({
        template: documentTemplate,
        parameters: [{ name: 'obra', value: 'Planta Norte' }],
        headerAttachment: expect.objectContaining({ messageType: 'DOCUMENT' }),
      }),
    )
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('rejects a header with the wrong safe media type and permits escape dismissal', async () => {
    const { onClose } = renderSelector()
    fireEvent.click(screen.getByRole('button', { name: /ficha_tecnica/i }))
    fireEvent.change(screen.getByLabelText('Adjuntar PDF'), {
      target: { files: [new File(['image'], 'foto.png', { type: 'image/png' })] },
    })

    expect(screen.getByRole('alert')).toHaveTextContent('Seleccioná un PDF')
    fireEvent(screen.getByRole('dialog'), new Event('cancel', { cancelable: true }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('keeps template loading and retry feedback accessible', () => {
    const { onReload } = renderSelector({ error: 'Sin conexión', status: 'error', templates: [] })
    expect(screen.getByRole('alert')).toHaveTextContent('Sin conexión')
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(onReload).toHaveBeenCalledTimes(2)
  })
})
