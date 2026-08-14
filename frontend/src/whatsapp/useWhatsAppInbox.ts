import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ApiError } from '../api/client'
import { getCustomer } from '../api/customers'
import {
  type ApiSession,
  createWhatsAppOpportunity,
  getOpportunityDetail,
} from '../api/opportunities'
import {
  getWhatsAppConversation,
  getWhatsAppMediaBlob,
  linkWhatsAppOpportunity,
  listWhatsAppConversationChanges,
  listWhatsAppConversations,
  listWhatsAppHumanTemplates,
  listWhatsAppMessageChanges,
  listWhatsAppMessages,
  markWhatsAppConversationRead,
  sendWhatsAppHumanTemplate,
  sendWhatsAppMessage,
  unlinkWhatsAppOpportunity,
  uploadWhatsAppMedia,
} from '../api/whatsapp'
import { useAuth } from '../auth/AuthContext'
import type { CustomerDetail } from '../customers/types'
import type { OpportunityDetail } from '../pipeline/types'
import { filterConversations, upsertConversations, upsertMessages } from './inbox-state'
import type {
  HumanTemplateSendInput,
  StagedWhatsAppAttachment,
  WhatsAppConversationDetail,
  WhatsAppConversationSummary,
  WhatsAppFilters,
  WhatsAppHumanTemplate,
  WhatsAppMessage,
  WhatsAppMessageType,
  WhatsAppSendIntent,
} from './types'

const POLLING_INTERVAL_MS = 5_000
const SEARCH_DEBOUNCE_MS = 300

type LoadStatus = 'idle' | 'loading' | 'ready' | 'error'

type PendingSend = {
  conversationId: number
  intent: WhatsAppSendIntent
  file: File | null
}

export type NewMessageInput = {
  body: string
  attachment: StagedWhatsAppAttachment | null
  retryOfMessageId?: number
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) return error.message
  return fallback
}

function createClientGeneratedId(): string {
  return crypto.randomUUID()
}

export function useWhatsAppInbox(initialConversationId?: number) {
  const { token, logout } = useAuth()
  const apiSession = useMemo<ApiSession>(
    () => ({ token: token ?? '', onUnauthorized: logout }),
    [logout, token],
  )
  const [conversations, setConversations] = useState<WhatsAppConversationSummary[]>([])
  const [conversationStatus, setConversationStatus] = useState<LoadStatus>('idle')
  const [conversationError, setConversationError] = useState<string | null>(null)
  const [nextConversationCursor, setNextConversationCursor] = useState<string | null>(null)
  const [conversationReloadKey, setConversationReloadKey] = useState(0)
  const [searchDraft, setSearchDraft] = useState('')
  const [search, setSearch] = useState('')
  const [waitingOnly, setWaitingOnly] = useState(false)
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [selectedConversationId, setSelectedConversationId] = useState<number | null>(
    initialConversationId ?? null,
  )
  const [selectedDetail, setSelectedDetail] = useState<WhatsAppConversationDetail | null>(null)
  const [detailStatus, setDetailStatus] = useState<LoadStatus>('idle')
  const [detailError, setDetailError] = useState<string | null>(null)
  const [messages, setMessages] = useState<WhatsAppMessage[]>([])
  const [messageStatus, setMessageStatus] = useState<LoadStatus>('idle')
  const [messageError, setMessageError] = useState<string | null>(null)
  const [nextMessageCursor, setNextMessageCursor] = useState<string | null>(null)
  const [selectedReloadKey, setSelectedReloadKey] = useState(0)
  const [isLoadingOlder, setIsLoadingOlder] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [sendError, setSendError] = useState<string | null>(null)
  const [failedSend, setFailedSend] = useState<PendingSend | null>(null)
  const [humanTemplates, setHumanTemplates] = useState<WhatsAppHumanTemplate[]>([])
  const [humanTemplateStatus, setHumanTemplateStatus] = useState<LoadStatus>('idle')
  const [humanTemplateError, setHumanTemplateError] = useState<string | null>(null)
  const [isLinking, setIsLinking] = useState(false)
  const [linkError, setLinkError] = useState<string | null>(null)
  const [isCreatingOpportunity, setIsCreatingOpportunity] = useState(false)
  const [customerDetail, setCustomerDetail] = useState<CustomerDetail | null>(null)
  const [opportunityDetail, setOpportunityDetail] = useState<OpportunityDetail | null>(null)
  const [contextStatus, setContextStatus] = useState<LoadStatus>('idle')
  const [contextError, setContextError] = useState<string | null>(null)
  const [contextReloadKey, setContextReloadKey] = useState(0)
  const [isOnline, setIsOnline] = useState(() => navigator.onLine)
  const [isDocumentVisible, setIsDocumentVisible] = useState(
    () => document.visibilityState === 'visible',
  )
  const [resyncKey, setResyncKey] = useState(0)

  const conversationSyncCursorRef = useRef<string | null>(null)
  const messageSyncCursorRef = useRef<string | null>(null)
  const conversationPollingRef = useRef(false)
  const messagePollingRef = useRef(false)
  const initialSelectionMadeRef = useRef(Boolean(initialConversationId))
  const selectedConversationIdRef = useRef<number | null>(null)

  const filters = useMemo<WhatsAppFilters>(
    () => ({ search, waitingOnly, unreadOnly }),
    [search, unreadOnly, waitingOnly],
  )
  const visibleConversations = useMemo(
    () => filterConversations(conversations, filters),
    [conversations, filters],
  )

  useEffect(() => {
    const timer = window.setTimeout(() => setSearch(searchDraft.trim()), SEARCH_DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
  }, [searchDraft])

  useEffect(() => {
    selectedConversationIdRef.current = selectedConversationId
  }, [selectedConversationId])

  useEffect(() => {
    void conversationReloadKey
    const controller = new AbortController()
    conversationSyncCursorRef.current = null
    setConversationStatus('loading')
    setConversationError(null)
    listWhatsAppConversations(
      {
        waitingOnly,
        unreadOnly,
        search,
      },
      { ...apiSession, signal: controller.signal },
    )
      .then((page) => {
        setConversations(page.items)
        setNextConversationCursor(page.next_page_cursor)
        conversationSyncCursorRef.current = page.sync_cursor
        setConversationStatus('ready')
        if (!initialSelectionMadeRef.current && page.items[0]) {
          initialSelectionMadeRef.current = true
          setSelectedConversationId(page.items[0].id)
        }
      })
      .catch((error: unknown) => {
        if (isAbortError(error)) return
        setConversationStatus('error')
        setConversationError(errorMessage(error, 'No pudimos cargar las conversaciones.'))
      })
    return () => controller.abort()
  }, [apiSession, conversationReloadKey, search, unreadOnly, waitingOnly])

  const pollConversationChanges = useCallback(async () => {
    if (conversationPollingRef.current) return
    const initialCursor = conversationSyncCursorRef.current
    if (!initialCursor) return
    conversationPollingRef.current = true
    try {
      let cursor = initialCursor
      let hasMore = true
      while (hasMore) {
        const page = await listWhatsAppConversationChanges(cursor, apiSession)
        setConversations((current) => upsertConversations(current, page.items))
        setSelectedDetail((current) => {
          if (!current) return current
          const updated = page.items.find((item) => item.id === current.id)
          if (!updated) return current
          const freshest = upsertConversations([current], [updated]).find(
            (item) => item.id === current.id,
          )
          return freshest ? { ...current, ...freshest } : current
        })
        cursor = page.next_cursor
        conversationSyncCursorRef.current = cursor
        hasMore = page.has_more
      }
      setConversationError(null)
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 422) {
        conversationSyncCursorRef.current = null
        setConversationReloadKey((current) => current + 1)
      } else {
        setConversationError(errorMessage(error, 'La bandeja está temporalmente desactualizada.'))
      }
    } finally {
      conversationPollingRef.current = false
    }
  }, [apiSession])

  const pollMessageChanges = useCallback(async () => {
    if (messagePollingRef.current) return
    const conversationId = selectedConversationIdRef.current
    const initialCursor = messageSyncCursorRef.current
    if (!conversationId || !initialCursor) return
    messagePollingRef.current = true
    try {
      let cursor = initialCursor
      let hasMore = true
      while (hasMore) {
        const page = await listWhatsAppMessageChanges(conversationId, cursor, apiSession)
        if (selectedConversationIdRef.current !== conversationId) return
        setMessages((current) => upsertMessages(current, page.items))
        cursor = page.next_cursor
        messageSyncCursorRef.current = cursor
        hasMore = page.has_more
      }
      setMessageError(null)
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 422) {
        messageSyncCursorRef.current = null
        if (selectedConversationIdRef.current === conversationId) {
          setSelectedReloadKey((key) => key + 1)
        }
      } else {
        setMessageError(errorMessage(error, 'Los mensajes están temporalmente desactualizados.'))
      }
    } finally {
      messagePollingRef.current = false
    }
  }, [apiSession])

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true)
      setResyncKey((current) => current + 1)
    }
    const handleOffline = () => setIsOnline(false)
    const handleVisibility = () => {
      const visible = document.visibilityState === 'visible'
      setIsDocumentVisible(visible)
      if (visible) setResyncKey((current) => current + 1)
    }
    const handleFocus = () => setResyncKey((current) => current + 1)
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    window.addEventListener('focus', handleFocus)
    document.addEventListener('visibilitychange', handleVisibility)
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
      window.removeEventListener('focus', handleFocus)
      document.removeEventListener('visibilitychange', handleVisibility)
    }
  }, [])

  useEffect(() => {
    void resyncKey
    if (!isOnline || !isDocumentVisible) return
    void pollConversationChanges()
    const timer = window.setInterval(() => void pollConversationChanges(), POLLING_INTERVAL_MS)
    return () => window.clearInterval(timer)
  }, [isDocumentVisible, isOnline, pollConversationChanges, resyncKey])

  useEffect(() => {
    void resyncKey
    if (!isOnline || !isDocumentVisible || !selectedConversationId) return
    void pollMessageChanges()
    const timer = window.setInterval(() => void pollMessageChanges(), POLLING_INTERVAL_MS)
    return () => window.clearInterval(timer)
  }, [isDocumentVisible, isOnline, pollMessageChanges, resyncKey, selectedConversationId])

  useEffect(() => {
    void selectedReloadKey
    if (!selectedConversationId) {
      setSelectedDetail(null)
      setMessages([])
      setDetailStatus('idle')
      setMessageStatus('idle')
      messageSyncCursorRef.current = null
      return
    }
    const controller = new AbortController()
    const session = { ...apiSession, signal: controller.signal }
    setDetailStatus('loading')
    setMessageStatus('loading')
    setDetailError(null)
    setMessageError(null)
    setSelectedDetail(null)
    setMessages([])
    messageSyncCursorRef.current = null

    Promise.all([
      getWhatsAppConversation(selectedConversationId, session),
      listWhatsAppMessages(selectedConversationId, null, session),
    ])
      .then(([detail, page]) => {
        if (controller.signal.aborted) return
        setSelectedDetail(detail)
        setConversations((current) => upsertConversations(current, [detail]))
        setMessages(page.items)
        setNextMessageCursor(page.next_before_cursor)
        messageSyncCursorRef.current = page.sync_cursor
        setDetailStatus('ready')
        setMessageStatus('ready')
        void markWhatsAppConversationRead(selectedConversationId, session)
          .then((readSummary) => {
            if (controller.signal.aborted) return
            setConversations((current) => upsertConversations(current, [readSummary]))
            setSelectedDetail((current) =>
              current && current.id === readSummary.id ? { ...current, ...readSummary } : current,
            )
          })
          .catch((error: unknown) => {
            if (isAbortError(error)) return
            setConversationError(errorMessage(error, 'No pudimos actualizar el estado de lectura.'))
          })
      })
      .catch((error: unknown) => {
        if (isAbortError(error)) return
        if (error instanceof ApiError && error.status === 404) {
          setSelectedConversationId(null)
          setDetailStatus('idle')
          setMessageStatus('idle')
          return
        }
        const message = errorMessage(error, 'No pudimos cargar esta conversación.')
        setDetailError(message)
        setMessageError(message)
        setDetailStatus('error')
        setMessageStatus('error')
      })
    return () => controller.abort()
  }, [apiSession, selectedConversationId, selectedReloadKey])

  useEffect(() => {
    void selectedConversationId
    setSendError(null)
    setFailedSend(null)
  }, [selectedConversationId])

  useEffect(() => {
    const expiry = selectedDetail?.window_expires_at
    if (!expiry || !selectedConversationId) return
    const delay = new Date(expiry).getTime() - Date.now() + 100
    if (delay <= 0 || delay > 2_147_000_000) return
    const timer = window.setTimeout(() => {
      void getWhatsAppConversation(selectedConversationId, apiSession)
        .then((detail) => {
          if (selectedConversationIdRef.current !== selectedConversationId) return
          setSelectedDetail(detail)
          setConversations((current) => upsertConversations(current, [detail]))
        })
        .catch((error: unknown) => {
          setDetailError(errorMessage(error, 'No pudimos actualizar la ventana de respuesta.'))
        })
    }, delay)
    return () => window.clearTimeout(timer)
  }, [apiSession, selectedConversationId, selectedDetail?.window_expires_at])

  useEffect(() => {
    void contextReloadKey
    const customerId = selectedDetail?.customer?.is_available ? selectedDetail.customer.id : null
    const opportunityId = selectedDetail?.active_opportunity?.is_available
      ? selectedDetail.active_opportunity.id
      : null
    if (!customerId && !opportunityId) {
      setCustomerDetail(null)
      setOpportunityDetail(null)
      setContextStatus('ready')
      setContextError(null)
      return
    }
    const controller = new AbortController()
    const session = { ...apiSession, signal: controller.signal }
    setContextStatus('loading')
    setContextError(null)
    Promise.allSettled([
      customerId ? getCustomer(customerId, session) : Promise.resolve(null),
      opportunityId ? getOpportunityDetail(opportunityId, session) : Promise.resolve(null),
    ]).then(([customerResult, opportunityResult]) => {
      if (controller.signal.aborted) return
      const customer = customerResult.status === 'fulfilled' ? customerResult.value : null
      const opportunity = opportunityResult.status === 'fulfilled' ? opportunityResult.value : null
      setCustomerDetail(customer)
      setOpportunityDetail(opportunity)
      const failed = customerResult.status === 'rejected' || opportunityResult.status === 'rejected'
      setContextStatus(failed ? 'error' : 'ready')
      setContextError(failed ? 'No pudimos completar todo el contexto comercial.' : null)
    })
    return () => controller.abort()
  }, [
    apiSession,
    selectedDetail?.active_opportunity?.id,
    selectedDetail?.active_opportunity?.is_available,
    selectedDetail?.customer?.id,
    selectedDetail?.customer?.is_available,
    contextReloadKey,
  ])

  const loadMoreConversations = useCallback(async () => {
    if (!nextConversationCursor) return
    try {
      const page = await listWhatsAppConversations(
        {
          pageCursor: nextConversationCursor,
          waitingOnly,
          unreadOnly,
          search,
        },
        apiSession,
      )
      setConversations((current) => upsertConversations(current, page.items))
      setNextConversationCursor(page.next_page_cursor)
    } catch (error: unknown) {
      setConversationError(errorMessage(error, 'No pudimos cargar más conversaciones.'))
    }
  }, [apiSession, nextConversationCursor, search, unreadOnly, waitingOnly])

  const loadOlderMessages = useCallback(async () => {
    if (!selectedConversationId || !nextMessageCursor || isLoadingOlder) return
    setIsLoadingOlder(true)
    try {
      const page = await listWhatsAppMessages(selectedConversationId, nextMessageCursor, apiSession)
      setMessages((current) => upsertMessages(current, page.items))
      setNextMessageCursor(page.next_before_cursor)
    } catch (error: unknown) {
      setMessageError(errorMessage(error, 'No pudimos cargar mensajes anteriores.'))
    } finally {
      setIsLoadingOlder(false)
    }
  }, [apiSession, isLoadingOlder, nextMessageCursor, selectedConversationId])

  const refreshSelectedConversation = useCallback(async () => {
    const conversationId = selectedConversationIdRef.current
    if (!conversationId) return
    const detail = await getWhatsAppConversation(conversationId, apiSession)
    if (selectedConversationIdRef.current !== conversationId) return
    setSelectedDetail(detail)
    setConversations((current) => upsertConversations(current, [detail]))
  }, [apiSession])

  const dispatchPendingSend = useCallback(
    async (pending: PendingSend): Promise<boolean> => {
      setIsSending(true)
      setSendError(null)
      let retryable = pending
      try {
        if (pending.intent.messageType !== 'TEXT' && !pending.intent.mediaRef) {
          if (!pending.file) throw new Error('Missing attachment')
          const uploaded = await uploadWhatsAppMedia(
            pending.file,
            pending.intent.messageType,
            apiSession,
          )
          retryable = {
            ...pending,
            intent: { ...pending.intent, mediaRef: uploaded.media_ref },
          }
          setFailedSend(retryable)
        }
        const response = await sendWhatsAppMessage(
          retryable.conversationId,
          retryable.intent,
          apiSession,
        )
        if (selectedConversationIdRef.current === retryable.conversationId) {
          setMessages((current) => upsertMessages(current, [response.message]))
          setSelectedDetail((current) =>
            current && current.id === retryable.conversationId
              ? {
                  ...current,
                  can_send_freeform: response.can_send_freeform,
                  window_expires_at: response.window_expires_at,
                  template_required: response.template_required,
                  reason: response.reason,
                }
              : current,
          )
        }
        setFailedSend(null)
        if (selectedConversationIdRef.current === retryable.conversationId) {
          void refreshSelectedConversation().catch((error: unknown) => {
            setConversationError(
              errorMessage(error, 'El mensaje se envió, pero falta actualizar la bandeja.'),
            )
          })
        }
        return true
      } catch (error: unknown) {
        if (selectedConversationIdRef.current === retryable.conversationId) {
          setFailedSend(retryable)
          setSendError(errorMessage(error, 'No pudimos enviar el mensaje.'))
        }
        return false
      } finally {
        setIsSending(false)
      }
    },
    [apiSession, refreshSelectedConversation],
  )

  const sendNewMessage = useCallback(
    (input: NewMessageInput): Promise<boolean> => {
      if (!selectedConversationId) return Promise.resolve(false)
      const messageType: WhatsAppMessageType = input.attachment
        ? input.attachment.messageType
        : 'TEXT'
      return dispatchPendingSend({
        conversationId: selectedConversationId,
        intent: {
          clientGeneratedId: createClientGeneratedId(),
          messageType,
          body: input.body.trim() || null,
          mediaRef: null,
          retryOfMessageId: input.retryOfMessageId ?? null,
        },
        file: input.attachment?.file ?? null,
      })
    },
    [dispatchPendingSend, selectedConversationId],
  )

  const retryFailedSend = useCallback(() => {
    if (!failedSend) return Promise.resolve(false)
    return dispatchPendingSend(failedSend)
  }, [dispatchPendingSend, failedSend])

  const resendMessage = useCallback(
    async (message: WhatsAppMessage): Promise<boolean> => {
      let attachment: StagedWhatsAppAttachment | null = null
      if (message.message_type !== 'TEXT') {
        const contentUrl = message.attachment?.content_url
        if (!contentUrl || !message.attachment?.is_available) {
          setSendError('El archivo original no está disponible para reenviar.')
          return false
        }
        try {
          const blob = await getWhatsAppMediaBlob(contentUrl, apiSession)
          attachment = {
            file: new File(
              [blob],
              message.attachment.filename ??
                (message.message_type === 'IMAGE' ? 'imagen' : 'documento.pdf'),
              { type: message.attachment.mime_type ?? blob.type },
            ),
            messageType: message.message_type,
            previewUrl: null,
          }
        } catch (error: unknown) {
          setSendError(errorMessage(error, 'No pudimos recuperar el archivo para reenviar.'))
          return false
        }
      }
      return sendNewMessage({
        body: message.body ?? '',
        attachment,
        retryOfMessageId: message.id,
      })
    },
    [apiSession, sendNewMessage],
  )

  const loadHumanTemplates = useCallback(async (): Promise<void> => {
    const conversationId = selectedConversationIdRef.current
    if (!conversationId) return
    setHumanTemplateStatus('loading')
    setHumanTemplateError(null)
    try {
      const templates = await listWhatsAppHumanTemplates(conversationId, apiSession)
      if (selectedConversationIdRef.current !== conversationId) return
      setHumanTemplates(templates)
      setHumanTemplateStatus('ready')
    } catch (error: unknown) {
      if (selectedConversationIdRef.current !== conversationId) return
      setHumanTemplateStatus('error')
      setHumanTemplateError(errorMessage(error, 'No pudimos cargar las plantillas aprobadas.'))
    }
  }, [apiSession])

  const sendHumanTemplate = useCallback(
    async (input: HumanTemplateSendInput): Promise<boolean> => {
      const conversationId = selectedConversationIdRef.current
      if (!conversationId) return false
      setIsSending(true)
      setSendError(null)
      try {
        const headerMedia = input.headerAttachment
          ? await uploadWhatsAppMedia(
              input.headerAttachment.file,
              input.headerAttachment.messageType,
              apiSession,
            )
          : null
        const response = await sendWhatsAppHumanTemplate(
          conversationId,
          input,
          createClientGeneratedId(),
          headerMedia?.media_ref ?? null,
          apiSession,
        )
        if (selectedConversationIdRef.current === conversationId) {
          setMessages((current) => upsertMessages(current, [response.message]))
          setSelectedDetail((current) =>
            current && current.id === conversationId
              ? {
                  ...current,
                  can_send_freeform: response.can_send_freeform,
                  window_expires_at: response.window_expires_at,
                  template_required: response.template_required,
                  reason: response.reason,
                }
              : current,
          )
          void refreshSelectedConversation().catch((error: unknown) => {
            setConversationError(
              errorMessage(error, 'El mensaje se envió, pero falta actualizar la bandeja.'),
            )
          })
        }
        return true
      } catch (error: unknown) {
        if (selectedConversationIdRef.current === conversationId) {
          setSendError(errorMessage(error, 'No pudimos enviar la plantilla.'))
        }
        return false
      } finally {
        setIsSending(false)
      }
    },
    [apiSession, refreshSelectedConversation],
  )

  const updateOpportunityLink = useCallback(
    async (opportunityId: number | null) => {
      if (!selectedConversationId) return
      setIsLinking(true)
      setLinkError(null)
      try {
        const detail = opportunityId
          ? await linkWhatsAppOpportunity(selectedConversationId, opportunityId, apiSession)
          : await unlinkWhatsAppOpportunity(selectedConversationId, apiSession)
        setSelectedDetail(detail)
        setConversations((current) => upsertConversations(current, [detail]))
      } catch (error: unknown) {
        setLinkError(errorMessage(error, 'No pudimos actualizar la oportunidad vinculada.'))
      } finally {
        setIsLinking(false)
      }
    },
    [apiSession, selectedConversationId],
  )

  const createOpportunity = useCallback(async () => {
    if (
      selectedDetail?.resolution_status !== 'RESOLVED' ||
      !selectedDetail.customer?.is_available
    ) {
      return
    }
    setIsCreatingOpportunity(true)
    setLinkError(null)
    try {
      await createWhatsAppOpportunity(selectedDetail.customer.id, apiSession)
      await refreshSelectedConversation()
    } catch (error: unknown) {
      setLinkError(errorMessage(error, 'No pudimos crear la oportunidad.'))
    } finally {
      setIsCreatingOpportunity(false)
    }
  }, [apiSession, refreshSelectedConversation, selectedDetail])

  return {
    conversations: visibleConversations,
    conversationStatus,
    conversationError,
    nextConversationCursor,
    searchDraft,
    setSearchDraft,
    waitingOnly,
    setWaitingOnly,
    unreadOnly,
    setUnreadOnly,
    selectedConversationId,
    selectConversation: setSelectedConversationId,
    selectedDetail,
    detailStatus,
    detailError,
    messages,
    messageStatus,
    messageError,
    nextMessageCursor,
    isLoadingOlder,
    isSending,
    sendError,
    failedSend,
    humanTemplates,
    humanTemplateStatus,
    humanTemplateError,
    isLinking,
    isCreatingOpportunity,
    linkError,
    customerDetail,
    opportunityDetail,
    contextStatus,
    contextError,
    isOnline,
    loadMoreConversations,
    loadOlderMessages,
    retryConversationLoad: () => setConversationReloadKey((current) => current + 1),
    retrySelectedLoad: () => setSelectedReloadKey((current) => current + 1),
    retryContextLoad: () => setContextReloadKey((current) => current + 1),
    clearSendError: () => setSendError(null),
    discardFailedSend: () => {
      setFailedSend(null)
      setSendError(null)
    },
    clearLinkError: () => setLinkError(null),
    sendNewMessage,
    retryFailedSend,
    resendMessage,
    loadHumanTemplates,
    sendHumanTemplate,
    updateOpportunityLink,
    createOpportunity,
  }
}
