import { useEffect, useMemo, useState } from 'react'

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
import { OpportunityDetailContent } from '../pipeline/OpportunityDetailContent'
import { QuoteModal } from '../pipeline/QuoteModal'
import type { LossReason, OpportunityDetail, Product, QuoteProductInput } from '../pipeline/types'
import { AppLink, navigateRoute, navigateToHistoryOrigin } from '../routing/router'
import { Button } from '../shared/Button'
import { ConfirmationDialog } from '../shared/ConfirmationDialog'
import { Icon } from '../shared/Icon'
import { InlineFeedback } from '../shared/InlineFeedback'
import { LoadingState } from '../shared/LoadingState'
import { Modal } from '../shared/Modal'

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
  opportunityId,
  surface = 'pipeline',
}: {
  opportunityId: number
  surface?: 'pipeline' | 'lost'
}) {
  const { token, logout } = useAuth()
  const [opportunity, setOpportunity] = useState<OpportunityDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<'not-found' | 'request' | null>(null)
  const [key, setKey] = useState(0)
  const [isReopenConfirmationOpen, setIsReopenConfirmationOpen] = useState(false)
  const [isReopening, setIsReopening] = useState(false)
  const [reopenError, setReopenError] = useState<string | null>(null)
  const [isLookingUpConversation, setIsLookingUpConversation] = useState(false)
  const [whatsAppFeedback, setWhatsAppFeedback] = useState<string | null>(null)
  const [isQuoteOpen, setIsQuoteOpen] = useState(false)
  const [quoteMode, setQuoteMode] = useState<'create' | 'edit'>('create')
  const [products, setProducts] = useState<Product[] | null>(null)
  const [isLoadingProducts, setIsLoadingProducts] = useState(false)
  const [productsError, setProductsError] = useState<string | null>(null)
  const [lossOpportunity, setLossOpportunity] = useState<OpportunityDetail | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const session = useMemo<ApiSession>(
    () => ({ token: token ?? '', onUnauthorized: logout }),
    [logout, token],
  )
  useEffect(() => {
    void key
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    getOpportunityDetail(opportunityId, { ...session, signal: controller.signal })
      .then((detail) => {
        if (detail.status === 'PERDIDA' && surface !== 'lost')
          navigateRoute({ kind: 'opportunity', opportunityId, surface: 'lost' }, { replace: true })
        setOpportunity(detail)
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
  const close = () => navigateToHistoryOrigin({ kind: 'workspace', workspace: surface })
  const handleReopen = async () => {
    if (!opportunity || !isEligibleForReopen(opportunity) || isReopening) return
    setIsReopening(true)
    setReopenError(null)
    try {
      await reopenOpportunity(opportunity.id, session)
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
    setIsLoadingProducts(true)
    setProductsError(null)
    listActiveProducts(session)
      .then((items) => setProducts(items.filter((item) => item.is_active)))
      .catch(() => setProductsError('No pudimos cargar los productos. Intentá nuevamente.'))
      .finally(() => setIsLoadingProducts(false))
  }

  const openQuote = (mode: 'create' | 'edit') => {
    setQuoteMode(mode)
    setIsQuoteOpen(true)
    if (!products && !isLoadingProducts) {
      loadProducts()
    }
  }

  const handleQuote = async (lines: QuoteProductInput[]) => {
    if (!opportunity) return
    if (quoteMode === 'edit') {
      const updated = await updateOpportunityQuoteProducts(
        opportunity.id,
        lines,
        opportunity.updated_at,
        session,
      )
      setOpportunity(updated)
    } else {
      await quoteOpportunity(opportunity.id, lines, session)
      setKey((current) => current + 1)
    }
    setIsQuoteOpen(false)
  }

  const move = async () => {
    if (!opportunity) return
    setActionError(null)
    try {
      if (opportunity.status === 'COTIZADA')
        await moveOpportunityToNegotiation(opportunity.id, session)
      if (opportunity.status === 'NEGOCIACION') await winOpportunity(opportunity.id, session)
      setKey((current) => current + 1)
    } catch {
      setActionError('No pudimos actualizar la oportunidad. Intentá nuevamente.')
    }
  }

  const handleLoss = async (reason: LossReason) => {
    if (!lossOpportunity) return
    await loseOpportunity(lossOpportunity.id, reason, session)
    setLossOpportunity(null)
    navigateRoute(
      { kind: 'opportunity', opportunityId: lossOpportunity.id, surface: 'lost' },
      { origin: { kind: 'workspace', workspace: 'pipeline' } },
    )
  }

  const actions = opportunity ? (
    <>
      {opportunity.status === 'NUEVA' ? (
        <Button onClick={() => openQuote('create')} variant='primary'>
          Cotizar
        </Button>
      ) : null}
      {opportunity.status === 'COTIZADA' || opportunity.status === 'NEGOCIACION' ? (
        <Button onClick={() => openQuote('edit')}>Editar cotización</Button>
      ) : null}
      {opportunity.status === 'COTIZADA' || opportunity.status === 'NEGOCIACION' ? (
        <Button onClick={() => void move()} variant='primary'>
          {opportunity.status === 'COTIZADA' ? 'Pasar a negociación' : 'Marcar ganada'}
        </Button>
      ) : null}
      <Button
        className='opportunity-whatsapp-action'
        disabled={isLookingUpConversation}
        onClick={() => void handleWhatsApp()}
      >
        <Icon name='whatsapp' />
        {isLookingUpConversation ? 'Buscando conversación…' : 'Abrir WhatsApp'}
      </Button>
      {isEligibleForReopen(opportunity) ? (
        <Button onClick={() => setIsReopenConfirmationOpen(true)} variant='primary'>
          Reabrir
        </Button>
      ) : null}
      {opportunity.status === 'NUEVA' ||
      opportunity.status === 'COTIZADA' ||
      opportunity.status === 'NEGOCIACION' ? (
        <Button onClick={() => setLossOpportunity(opportunity)} variant='danger'>
          Marcar perdida
        </Button>
      ) : null}
    </>
  ) : undefined

  if (opportunity && isQuoteOpen) {
    return (
      <QuoteModal
        isLoadingProducts={isLoadingProducts}
        isOpen
        mode={quoteMode}
        onClose={() => setIsQuoteOpen(false)}
        onConfirm={handleQuote}
        onRetryProducts={() => {
          setProducts(null)
          loadProducts()
        }}
        opportunity={opportunity}
        products={products}
        productsError={productsError}
      />
    )
  }

  return (
    <Modal isOpen onClose={close} size='large' title='Detalle de oportunidad'>
      <div className='px-4 pt-3'>
        <AppLink
          onClick={(event) => {
            event.preventDefault()
            close()
          }}
          to={{ kind: 'workspace', workspace: surface }}
        >
          Volver al {surface === 'lost' ? 'Perdidas' : 'Pipeline'}
        </AppLink>
      </div>
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
        <div className='max-h-[calc(100dvh-10rem)] overflow-y-auto p-4'>
          {whatsAppFeedback ? (
            <div className='mb-3'>
              <InlineFeedback
                message={whatsAppFeedback}
                onDismiss={() => setWhatsAppFeedback(null)}
              />
            </div>
          ) : null}
          {actionError ? (
            <div className='mb-3'>
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
