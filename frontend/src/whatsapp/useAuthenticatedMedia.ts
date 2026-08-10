import { useEffect, useState } from 'react'

import { getWhatsAppMediaBlob } from '../api/whatsapp'
import { useAuth } from '../auth/AuthContext'

export function useAuthenticatedMedia(contentUrl: string | null) {
  const { token, logout } = useAuth()
  const [objectUrl, setObjectUrl] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(Boolean(contentUrl))
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!contentUrl) {
      setObjectUrl(null)
      setIsLoading(false)
      setError(false)
      return
    }
    const controller = new AbortController()
    let createdUrl: string | null = null
    setObjectUrl(null)
    setIsLoading(true)
    setError(false)
    getWhatsAppMediaBlob(contentUrl, {
      token: token ?? '',
      onUnauthorized: logout,
      signal: controller.signal,
    })
      .then((blob) => {
        if (controller.signal.aborted) return
        createdUrl = URL.createObjectURL(blob)
        setObjectUrl(createdUrl)
      })
      .catch((requestError: unknown) => {
        if (requestError instanceof DOMException && requestError.name === 'AbortError') {
          return
        }
        setError(true)
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false)
      })

    return () => {
      controller.abort()
      if (createdUrl) URL.revokeObjectURL(createdUrl)
    }
  }, [contentUrl, logout, token])

  return { objectUrl, isLoading, error }
}
