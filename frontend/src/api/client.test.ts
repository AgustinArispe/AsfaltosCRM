import { afterEach, describe, expect, it, vi } from 'vitest'

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
  vi.resetModules()
})

describe('apiBlobRequest', () => {
  it.each([
    '/api/whatsapp/attachments/44/content',
    '/api/whatsapp/media/22222222-2222-4222-8222-222222222222/content',
  ])('uses the configured backend origin for private media: %s', async (contentUrl) => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://becrm.example.test/api')
    const fetchMock = vi.fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>(
      () =>
        Promise.resolve(
          new Response('private media', { headers: { 'Content-Type': 'audio/ogg' } }),
        ),
    )
    vi.stubGlobal('fetch', fetchMock)
    const { apiBlobRequest } = await import('./client')

    const blob = await apiBlobRequest(contentUrl, { token: 'private-media-token' })

    expect(blob.type).toBe('audio/ogg')
    expect(fetchMock).toHaveBeenCalledWith(
      `https://becrm.example.test${contentUrl}`,
      expect.objectContaining({ headers: expect.any(Headers) }),
    )
    const request = fetchMock.mock.calls[0]
    expect(new Headers(request[1]?.headers).get('Authorization')).toBe('Bearer private-media-token')
    expect(String(fetchMock.mock.calls[0]?.[0])).not.toMatch(/^\/api\//)
  })

  it('rejects an external or non-WhatsApp URL before fetching', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const { apiBlobRequest } = await import('./client')

    await expect(
      apiBlobRequest('https://lookaside.fbsbx.com/provider-media', {
        token: 'private-media-token',
      }),
    ).rejects.toEqual(expect.objectContaining<{ status: number }>({ status: 422 }))
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
