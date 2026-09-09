import { useEffect, useMemo, useRef, useState } from 'react'

import { ApiError } from '../api/client'
import {
  type ApiSession,
  getOpportunityDetail,
  loseOpportunity,
  moveOpportunityToNegotiation,
  quoteOpportunity,
  reopenOpportunity,
  updateOpportunityQuoteProducts,
  winOpportunity,
} from '../api/opportunities'
import { listActiveProducts } from '../api/products'
import { listWhatsAppConversations } from '../api/whatsapp'
import { useAuth } from '../auth/AuthContext'
import { LossModal } from '../pipeline/LossModal'
import { OpportunityContextPanel } from '../pipeline/OpportunityContextPanel'
import {
  OpportunityDetailContent,
  OpportunityDetailModalHeader,
} from '../pipeline/OpportunityDetailContent'
import { QuoteModal } from '../pipeline/QuoteModal'
import type { LossReason, OpportunityDetail, Product, QuoteProductInput } from '../pipeline/types'
import type { ActiveProductCatalog } from '../pipeline/useActiveProductCatalog'
import { AppLink, navigate, navigateRoute, navigateToHistoryOrigin } from '../routing/router'
import { Button } from '../shared/Button'
import { ConfirmationDialog } from '../shared/ConfirmationDialog'
import { Icon } from '../shared/Icon'
import { Modal } from '../shared/Modal'
import { InlineFeedback, LoadingState } from '../shared/StatusStates'

function normalizedPhone(value: string | null): string | null {
  const normalized = value?.replace(/\D/g, '') ?? ''
  return normalized || null
}

function isEligibleForReopen(opportunity: OpportunityDetail): boolean {
  return (
    opportunity.status === 'PERDIDA' &&
    opportunity.products.some((line) => Number(line.quantity_kg) > 0)
  )
}

export function OpportunityDetailPage({
  cachedOpportunity,
  catalog,
  onOpportunityUpdated,
  opportunityId,
  surface = 'pipeline',
}: {
  cachedOpportunity?: OpportunityDetail
  catalog?: ActiveProductCatalog
  onOpportunityUpdated?: (opportunity: OpportunityDetail) => void
  opportunityId: number
  surface?: 'pipeline' | 'lost' | 'won'
}) {
  const { token, logout } = useAuth()
  const returnFocusRef = useRef<HTMLElement | null>(
    document.activeElement instanceof HTMLElement ? document.activeElement : null,
  )
  const [opportunity, setOpportunity] = useState<OpportunityDetail | null>(
    cachedOpportunity ?? null,
  )
  const [loading, setLoading] = useState(!cachedOpportunity)
  const [error, setError] = useState<'not-found' | 'request' | null>(null)
  const [key, setKey] = useState(0)
  const [isReopenConfirmationOpen, setIsReopenConfirmationOpen] = useState(false)
  const [isReopening, setIsReopening] = useState(false)
  const [reopenError, setReopenError] = useState<string | null>(null)
  const [isLookingUpConversation, setIsLookingUpConversation] = useState(false)
  const [whatsAppFeedback, setWhatsAppFeedback] = useState<string | null>(null)
  const [isQuoteOpen, setIsQuoteOpen] = useState(false)
  const [quoteMode, setQuoteMode] = useState<'create' | 'edit'>('create')
  const [localProducts, setLocalProducts] = useState<Product[] | null>(null)
  const [isLoadingLocalProducts, setIsLoadingLocalProducts] = useState(false)
  const [localProductsError, setLocalProductsError] = useState<string | null>(null)
  const [lossOpportunity, setLossOpportunity] = useState<OpportunityDetail | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [isMutating, setIsMutating] = useState(false)
  const requestGenerationRef = useRef(0)
  const opportunityRef = useRef(opportunity)
  const cachedOpportunityRef = useRef(cachedOpportunity)
  const onOpportunityUpdatedRef = useRef(onOpportunityUpdated)
  opportunityRef.current = opportunity
  cachedOpportunityRef.current = cachedOpportunity
  onOpportunityUpdatedRef.current = onOpportunityUpdated
  const session = useMemo<ApiSession>(
    () => ({ token: token ?? '', onUnauthorized: logout }),
    [logout, token],
  )
  useEffect(() => {
    void key
    const controller = new AbortController()
    const generation = requestGenerationRef.current + 1
    requestGenerationRef.current = generation
    setLoading(
      cachedOpportunityRef.current?.id !== opportunityId &&
        opportunityRef.current?.id !== opportunityId,
    )
    setError(null)
    getOpportunityDetail(opportunityId, { ...session, signal: controller.signal })
      .then((detail) => {
        if (generation !== requestGenerationRef.current) return
        if (surface === 'won' && detail.status !== 'GANADA')
          navigateRoute(
            { kind: 'opportunity', opportunityId, surface: 'pipeline' },
            { replace: true },
          )
        setOpportunity(detail)
        onOpportunityUpdatedRef.current?.(detail)
      })
      .catch((value: unknown) => {
        if (!(value instanceof DOMException && value.name === 'AbortError'))
          setError(value instanceof ApiError && value.status === 404 ? 'not-found' : 'request')
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [key, opportunityId, session, surface])
  const close = () => {
    const previousFocus = returnFocusRef.current
    if (surface === 'won') navigate(`/won${window.location.search}`)
    else navigateToHistoryOrigin({ kind: 'workspace', workspace: surface })
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        const pipelineTrigger = document.querySelector<HTMLElement>(
          `[data-opportunity-id="${opportunityId}"] .pipeline-card__button`,
        )
        const fallbackHeading = document.querySelector<HTMLElement>('[data-page-heading]')
        const target = pipelineTrigger ?? (previousFocus?.isConnected ? previousFocus : null)
        const focusTarget = target ?? fallbackHeading
        focusTarget?.focus()
      })
    })
  }
  const handleReopen = async () => {
    if (!opportunity || !isEligibleForReopen(opportunity) || isReopening) return
    requestGenerationRef.current += 1
    setIsReopening(true)
    setReopenError(null)
    try {
      const updated = await reopenOpportunity(opportunity.id, session)
      setOpportunity(updated)
      onOpportunityUpdated?.(updated)
      setIsReopenConfirmationOpen(false)
      setReopenError(null)
      navigateRoute(
        { kind: 'opportunity', opportunityId: opportunity.id, surface: 'pipeline' },
        { origin: { kind: 'workspace', workspace: 'lost' } },
      )
    } catch {
      setReopenError(
        'No pudimos reabrir la oportunidad. Su estado o cotización puede haber cambiado.',
      )
      setKey((current) => current + 1)
    } finally {
      setIsReopening(false)
    }
  }

  const handleWhatsApp = async () => {
    if (!opportunity || isLookingUpConversation) return
    setIsLookingUpConversation(true)
    setWhatsAppFeedback(null)
    try {
      const phone = normalizedPhone(opportunity.customer.phone)
      const searches = phone
        ? [phone, opportunity.customer.company ?? opportunity.customer.name]
        : [opportunity.customer.company ?? opportunity.customer.name]
      let conversationId: number | null = null
      for (const search of searches) {
        const page = await listWhatsAppConversations(
          { limit: 50, waitingOnly: false, unreadOnly: false, search },
          session,
        )
        const exactPhone = phone
          ? page.items.find((item) => normalizedPhone(item.external_phone) === phone)
          : undefined
        const customerMatch = page.items.find(
          (item) => item.customer?.id === opportunity.customer.id,
        )
        conversationId = exactPhone?.id ?? customerMatch?.id ?? null
        if (conversationId) break
      }
      if (conversationId) {
        navigateRoute(
          { kind: 'conversation', conversationId },
          { origin: { kind: 'opportunity', opportunityId: opportunity.id, surface } },
        )
      } else {
        setWhatsAppFeedback('No existe una conversación interna vinculada.')
      }
    } catch {
      setWhatsAppFeedback('No pudimos buscar una conversación interna. Intentá nuevamente.')
    } finally {
      setIsLookingUpConversation(false)
    }
  }

  const loadProducts = () => {
    if (catalog) {
      void catalog.load().catch(() => undefined)
      return
    }
    setIsLoadingLocalProducts(true)
    setLocalProductsError(null)
    listActiveProducts(session)
      .then((items) => setLocalProducts(items.filter((item) => item.is_active)))
      .catch(() => setLocalProductsError('No pudimos cargar los productos. Intentá nuevamente.'))
      .finally(() => setIsLoadingLocalProducts(false))
  }

  const openQuote = (mode: 'create' | 'edit') => {
    setQuoteMode(mode)
    setIsQuoteOpen(true)
    if (!(catalog?.products ?? localProducts) && !(catalog?.isLoading ?? isLoadingLocalProducts)) {
      loadProducts()
    }
  }

  const handleQuote = async (lines: QuoteProductInput[]) => {
    if (!opportunity) return
    requestGenerationRef.current += 1
    if (quoteMode === 'edit') {
      const updated = await updateOpportunityQuoteProducts(
        opportunity.id,
        lines,
        opportunity.updated_at,
        session,
      )
      setOpportunity(updated)
      onOpportunityUpdated?.(updated)
    } else {
      const updated = await quoteOpportunity(opportunity.id, lines, session)
      setOpportunity(updated)
      onOpportunityUpdated?.(updated)
    }
    setIsQuoteOpen(false)
  }

  const move = async () => {
    if (!opportunity || isMutating) return
    requestGenerationRef.current += 1
    setActionError(null)
    setIsMutating(true)
    try {
      const updated =
        opportunity.status === 'COTIZADA'
          ? await moveOpportunityToNegotiation(opportunity.id, session)
          : await winOpportunity(opportunity.id, session)
      setOpportunity(updated)
      onOpportunityUpdated?.(updated)
    } catch {
      setActionError('No pudimos actualizar la oportunidad. Intentá nuevamente.')
    } finally {
      setIsMutating(false)
    }
  }

  const handleLoss = async (reason: LossReason) => {
    if (!lossOpportunity) return
    requestGenerationRef.current += 1
    const updated = await loseOpportunity(lossOpportunity.id, reason, session)
    setOpportunity(updated)
    onOpportunityUpdated?.(updated)
    setLossOpportunity(null)
    navigate('/dashboard')
  }

  const actions = opportunity ? (
    <>
      {opportunity.status === 'NUEVA' ? (
        <Button
          className='opportunity-detail__action'
          onClick={() => openQuote('create')}
          variant='primary'
        >
          Cotizar
        </Button>
      ) : null}
      {opportunity.status === 'COTIZADA' || opportunity.status === 'NEGOCIACION' ? (
        <Button
          className='opportunity-detail__action'
          disabled={isMutating}
          isLoading={isMutating}
          onClick={() => void move()}
          variant='primary'
        >
          {isMutating
            ? 'Actualizando…'
            : opportunity.status === 'COTIZADA'
              ? 'Pasar a negociación'
              : 'Marcar ganada'}
        </Button>
      ) : null}
      {opportunity.status === 'COTIZADA' || opportunity.status === 'NEGOCIACION' ? (
        <Button className='opportunity-detail__action' onClick={() => openQuote('edit')}>
          Editar cotización
        </Button>
      ) : null}
      <Button
        className='opportunity-detail__action opportunity-whatsapp-action'
        disabled={isLookingUpConversation}
        isLoading={isLookingUpConversation}
        onClick={() => void handleWhatsApp()}
      >
        <Icon name='whatsapp' />
        {isLookingUpConversation ? 'Buscando conversación…' : 'Abrir WhatsApp'}
      </Button>
      {isEligibleForReopen(opportunity) ? (
        <Button
          className='opportunity-detail__action'
          onClick={() => setIsReopenConfirmationOpen(true)}
          variant='primary'
        >
          Reabrir
        </Button>
      ) : null}
      {opportunity.status === 'NUEVA' ||
      opportunity.status === 'COTIZADA' ||
      opportunity.status === 'NEGOCIACION' ? (
        <Button
          className='opportunity-detail__action opportunity-detail__action--destructive'
          onClick={() => setLossOpportunity(opportunity)}
          variant='danger'
        >
          Marcar perdida
        </Button>
      ) : null}
    </>
  ) : undefined

  if (opportunity && isQuoteOpen) {
    return (
      <QuoteModal
        isLoadingProducts={catalog?.isLoading ?? isLoadingLocalProducts}
        isOpen
        mode={quoteMode}
        onClose={() => setIsQuoteOpen(false)}
        onConfirm={handleQuote}
        onRetryProducts={() => {
          if (catalog) void catalog.retry().catch(() => undefined)
          else {
            setLocalProducts(null)
            loadProducts()
          }
        }}
        opportunity={opportunity}
        products={catalog?.products ?? localProducts}
        productsError={catalog?.error ?? localProductsError}
      />
    )
  }

  return (
    <Modal
      closeLabel='Cerrar detalle de oportunidad'
      isOpen
      onClose={close}
      renderHeader={({ titleId }) => (
        <OpportunityDetailModalHeader
          opportunity={opportunity}
          returnAffordance={
            <AppLink
              className='inline-flex items-center gap-1 rounded-[var(--radius-control)] text-[var(--action-secondary)] outline-none hover:underline focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]'
              onClick={(event) => {
                event.preventDefault()
                close()
              }}
              to={{ kind: 'workspace', workspace: surface }}
            >
              <Icon className='size-3.5' name='chevron-left' />
              {surface === 'won'
                ? 'Volver a Ganadas'
                : `Volver al ${surface === 'lost' ? 'Perdidas' : 'Pipeline'}`}
            </AppLink>
          }
          titleId={titleId}
        />
      )}
      returnFocusTo={returnFocusRef.current}
      size='opportunity'
      title={
        opportunity?.customer.company ?? opportunity?.customer.name ?? 'Detalle de oportunidad'
      }
    >
      {loading ? (
        <LoadingState label='Cargando oportunidad…' />
      ) : error || !opportunity ? (
        <div className='p-5'>
          <h3 className='text-lg font-semibold'>
            {error === 'not-found'
              ? 'Oportunidad no encontrada'
              : 'No pudimos cargar la oportunidad'}
          </h3>
          {error === 'not-found' ? (
            <p className='mt-2 text-sm text-[var(--text-secondary)]'>
              La oportunidad no está disponible.
            </p>
          ) : (
            <Button className='mt-4' onClick={() => setKey((value) => value + 1)}>
              Reintentar
            </Button>
          )}
        </div>
      ) : (
        <div>
          {whatsAppFeedback ? (
            <div className='px-5 pt-4 sm:px-6'>
              <InlineFeedback
                message={whatsAppFeedback}
                onDismiss={() => setWhatsAppFeedback(null)}
              />
            </div>
          ) : null}
          {actionError ? (
            <div className='px-5 pt-4 sm:px-6'>
              <InlineFeedback message={actionError} onDismiss={() => setActionError(null)} />
            </div>
          ) : null}
          <OpportunityDetailContent
            actions={actions}
            contextual={
              <OpportunityContextPanel
                key={opportunity.id}
                opportunity={opportunity}
                session={session}
              />
            }
            opportunity={opportunity}
          />
        </div>
      )}
      <ConfirmationDialog
        confirmLabel='Reabrir en negociación'
        description='La oportunidad volverá a Negociación y conservará su historial de pérdida.'
        error={reopenError}
        isOpen={isReopenConfirmationOpen}
        isPending={isReopening}
        onCancel={() => {
          if (!isReopening) {
            setIsReopenConfirmationOpen(false)
            setReopenError(null)
          }
        }}
        onConfirm={() => void handleReopen()}
        pendingLabel='Reabriendo…'
        title='Reabrir oportunidad'
      >
        <p className='text-sm text-[var(--text-secondary)]'>
          El destino lo determina FAA CRM: Negociación.
        </p>
      </ConfirmationDialog>
      <LossModal
        onClose={() => setLossOpportunity(null)}
        onConfirm={handleLoss}
        opportunity={lossOpportunity}
      />
    </Modal>
  )
}
