import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MessageBubble } from './MessageBubble'
import type { WhatsAppMessage, WhatsAppMessageType } from './types'

const authState = vi.hoisted(() => ({ logout: vi.fn() }))

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({ token: 'private-media-token', logout: authState.logout }),
}))

function mediaMessage(
  messageType: WhatsAppMessageType,
  storageStatus: 'PENDING' | 'AVAILABLE' | 'FAILED',
): WhatsAppMessage {
  const contentUrl = storageStatus === 'FAILED' ? null : '/api/whatsapp/attachments/44/content'
  return {
    id: 12,
    conversation_id: 4,
    external_message_id: 'wamid.private-media',
    client_generated_id: null,
    direction: 'INBOUND',
    message_type: messageType,
    origin: 'HUMAN',
    body: null,
    template_name: null,
    template_language: null,
    sent_by: null,
    retry_of_message_id: null,
    is_retry: false,
    message_at: '2026-09-22T12:00:00Z',
    attachment: {
      id: 44,
      media_type: messageType,
      mime_type: messageType === 'IMAGE' ? 'image/jpeg' : 'audio/ogg',
      filename: messageType === 'IMAGE' ? 'obra.jpg' : null,
      size_bytes: 128,
      storage_status: storageStatus,
      is_available: storageStatus === 'AVAILABLE',
      content_url: contentUrl,
    },
    status: {
      dispatch_state: null,
      provider_state: 'RECEIVED',
      accepted_at: null,
      sent_at: null,
      delivered_at: null,
      read_at: null,
      failed_at: null,
      error_code: null,
      error_message: null,
    },
    created_at: '2026-09-22T12:00:00Z',
    updated_at: '2026-09-22T12:00:00Z',
    resource_updated_at: '2026-09-22T12:00:00Z',
  }
}

describe('MessageBubble authenticated media', () => {
  beforeEach(() => {
    authState.logout.mockReset()
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(new Response(new Blob(['media']), { status: 200 }))),
    )
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      value: vi.fn(() => 'blob:http://localhost/private-media'),
    })
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      value: vi.fn(),
    })
  })

  afterEach(() => vi.unstubAllGlobals())

  it('fetches a pending image privately and renders the resulting blob preview', async () => {
    const { unmount } = render(
      <MessageBubble
        isSending={false}
        message={mediaMessage('IMAGE', 'PENDING')}
        onResend={vi.fn()}
      />,
    )

    const image = await screen.findByRole('img', { name: 'Imagen obra.jpg' })
    expect(image).toHaveAttribute('src', 'blob:http://localhost/private-media')
    expect(fetch).toHaveBeenCalledWith(
      '/api/whatsapp/attachments/44/content',
      expect.objectContaining({
        headers: expect.any(Headers),
        signal: expect.any(AbortSignal),
      }),
    )
    const request = vi.mocked(fetch).mock.calls[0]
    expect(new Headers(request[1]?.headers).get('Authorization')).toBe('Bearer private-media-token')
    expect(String(image.getAttribute('src'))).not.toContain('facebook')

    unmount()
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:http://localhost/private-media')
  })

  it('renders available voice audio as a labelled non-autoplaying player', async () => {
    render(
      <MessageBubble
        isSending={false}
        message={mediaMessage('AUDIO', 'AVAILABLE')}
        onResend={vi.fn()}
      />,
    )

    const player = await screen.findByLabelText('Audio adjunto')
    expect(player).toHaveAttribute('controls')
    expect(player).not.toHaveAttribute('autoplay')
    expect(player).toHaveAttribute('src', 'blob:http://localhost/private-media')
  })

  it('shows a failed-media state without requesting a provider or filesystem URL', async () => {
    render(
      <MessageBubble
        isSending={false}
        message={mediaMessage('IMAGE', 'FAILED')}
        onResend={vi.fn()}
      />,
    )

    expect(screen.getByText('Archivo no disponible')).toHaveAttribute('role', 'status')
    await waitFor(() => expect(fetch).not.toHaveBeenCalled())
  })
})
