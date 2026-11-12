import { useEffect, useMemo, useRef, useState } from 'react'

import { ApiError } from '../api/client'
import {
  type ApiSession,
  deleteOpportunity,
  followUpOpportunity,
  getOpportunityDetail,
  loseOpportunity,
  prepareOpportunityQuote,
  quoteOpportunity,
  regressOpportunityStage,
  reopenOpportunity,
  updateOpportunityQuoteProducts,
  winOpportunity,
} from '../api/opportunities'
import { listActiveProducts } from '../api/products'
import { openWhatsAppConversationForOpportunity } from '../api/whatsapp'
import { useAuth } from '../auth/AuthContext'
import { OPPORTUNITY_STATUS_LABELS, STAGE_BY_STATUS } from '../pipeline/config'
import { LossModal } from '../pipeline/LossModal'
import { OpportunityContextPanel } from '../pipeline/OpportunityContextPanel'
import {
  OpportunityDetailContent,
  OpportunityDetailModalHeader,
} from '../pipeline/OpportunityDetailContent'
import { isOpportunityOverdue } from '../pipeline/overdue'
import { QuoteModal } from '../pipeline/QuoteModal'
import { StageNoteConfirmation } from '../pipeline/StageNoteConfirmation'
import type {
  LossReason,
  OpportunityDetail,
  PipelineStatus,
  Product,
  QuoteProductInput,
} from '../pipeline/types'
import type { ActiveProductCatalog } from '../pipeline/useActiveProductCatalog'
import { AppLink, navigate, navigateRoute, navigateToHistoryOrigin } from '../routing/router'
import { Button } from '../shared/Button'
import { ConfirmationDialog } from '../shared/ConfirmationDialog'
import { Icon } from '../shared/Icon'
import { Modal } from '../shared/Modal'
import { InlineFeedback, LoadingState } from '../shared/StatusStates'

function hasComparablePhone(value: string | null): boolean {
  const comparable = value?.trim().replace(/[\s()-]/g, '') ?? ''
  return [...comparable].filter((character) => /[0-9]/.test(character)).length >= 7
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
  onClose,
  onOpportunityDeleted,
  onOpportunityUpdated,
  opportunityId,
  surface = 'pipeline',
}: {
  cachedOpportunity?: OpportunityDetail
  catalog?: ActiveProductCatalog
  onClose?: () => void
  onOpportunityDeleted?: (opportunityId: number) => void
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
  const [isDeleteConfirmationOpen, setIsDeleteConfirmationOpen] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
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
  const [isForwardConfirmationOpen, setIsForwardConfirmationOpen] = useState(false)
  const [pendingRegression, setPendingRegression] = useState<{
    fromStatus: PipelineStatus
    targetStatus: PipelineStatus
  } | null>(null)
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
    if (onClose) onClose()
    else if (surface === 'won') navigate(`/won${window.location.search}`)
    else if (surface === 'lost') navigate(`/lost${window.location.search}`)
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
  const handleReopen = async (note: string) => {
    if (!opportunity || !isEligibleForReopen(opportunity) || isReopening) return
    requestGenerationRef.current += 1
    setIsReopening(true)
    setReopenError(null)
    try {
      const updated = await reopenOpportunity(opportunity.id, note, session)
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
      const conversation = await openWhatsAppConversationForOpportunity(opportunity.id, session)
      navigateRoute(
        { kind: 'conversation', conversationId: conversation.id },
        { origin: { kind: 'opportunity', opportunityId: opportunity.id, surface } },
      )
    } catch {
      setWhatsAppFeedback('No pudimos iniciar WhatsApp para este contacto. Verificá su teléfono.')
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

  const handleQuote = async (lines: QuoteProductInput[], note: string, province?: string) => {
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
      const updated = await quoteOpportunity(opportunity.id, lines, note, session, province)
      setOpportunity(updated)
      onOpportunityUpdated?.(updated)
    }
    setIsQuoteOpen(false)
  }

  const move = async (note: string, province?: string) => {
    if (!opportunity || isMutating) return
    requestGenerationRef.current += 1
    setActionError(null)
    setIsMutating(true)
    try {
      const updated =
        opportunity.status === 'NUEVA'
          ? await prepareOpportunityQuote(opportunity.id, note, session)
          : await winOpportunity(opportunity.id, note, session, province)
      setOpportunity(updated)
      onOpportunityUpdated?.(updated)
      setIsForwardConfirmationOpen(false)
    } catch {
      setActionError('No pudimos actualizar la oportunidad. Intentá nuevamente.')
    } finally {
      setIsMutating(false)
    }
  }

  const markUpToDate = async () => {
    if (!opportunity || isMutating) return
    requestGenerationRef.current += 1
    setActionError(null)
    setIsMutating(true)
    try {
      const updated = await followUpOpportunity(
        opportunity.id,
        opportunity.follow_up_since ?? opportunity.current_status_entered_at,
        session,
      )
      setOpportunity(updated)
      onOpportunityUpdated?.(updated)
      window.dispatchEvent(new Event('faa-notification-attention-refresh'))
    } catch {
      setActionError('No pudimos marcarla al día. Actualizá el detalle e intentá nuevamente.')
    } finally {
      setIsMutating(false)
    }
  }

  const confirmRegression = async (note: string) => {
    if (!opportunity || !pendingRegression || isMutating) return
    setActionError(null)
    setIsMutating(true)
    try {
      const updated = await regressOpportunityStage(
        opportunity.id,
        pendingRegression.fromStatus,
        pendingRegression.targetStatus,
        note,
        session,
      )
      setOpportunity(updated)
      onOpportunityUpdated?.(updated)
      setPendingRegression(null)
      if (surface === 'won') {
        navigateRoute(
          { kind: 'opportunity', opportunityId: opportunity.id, surface: 'pipeline' },
          { replace: true },
        )
      }
    } catch {
      setActionError('No pudimos atrasar la oportunidad. Su etapa puede haber cambiado.')
    } finally {
      setIsMutating(false)
    }
  }

  const handleLoss = async (reason: LossReason, reasonDetail: string | null, note: string) => {
    if (!lossOpportunity) return
    requestGenerationRef.current += 1
    const updated = await loseOpportunity(lossOpportunity.id, reason, reasonDetail, note, session)
    setOpportunity(updated)
    onOpportunityUpdated?.(updated)
    setLossOpportunity(null)
    navigate('/dashboard')
  }

  const handleDelete = async () => {
    if (!opportunity || isDeleting) return
    setIsDeleting(true)
    setDeleteError(null)
    try {
      await deleteOpportunity(opportunity.id, session)
      onOpportunityDeleted?.(opportunity.id)
      setIsDeleteConfirmationOpen(false)
      close()
    } catch {
      setDeleteError('No pudimos eliminar la oportunidad. Intentá nuevamente.')
    } finally {
      setIsDeleting(false)
    }
  }

  const actions = opportunity ? (
    <>
      {isOpportunityOverdue(
        opportunity.status,
        opportunity.follow_up_since ?? opportunity.current_status_entered_at,
      ) ? (
        <Button
          className='opportunity-detail__action'
          disabled={isMutating}
          onClick={() => void markUpToDate()}
        >
          <Icon name='check-circle' /> Marcar al día
        </Button>
      ) : null}
      {opportunity.status === 'PARA_COTIZAR' ? (
        <Button
          className='opportunity-detail__action'
          onClick={() => openQuote('create')}
          variant='primary'
        >
          <Icon name={STAGE_BY_STATUS.get('COTIZADA')?.icon ?? 'document'} />
          Cotizar
        </Button>
      ) : null}
      {opportunity.status === 'NUEVA' || opportunity.status === 'COTIZADA' ? (
        <Button
          className='opportunity-detail__action'
          disabled={isMutating}
          isLoading={isMutating}
          onClick={() => setIsForwardConfirmationOpen(true)}
          variant='primary'
        >
          <Icon
            name={
              STAGE_BY_STATUS.get(opportunity.status === 'NUEVA' ? 'PARA_COTIZAR' : 'GANADA')
                ?.icon ?? 'document'
            }
          />
          {isMutating
            ? 'Actualizando…'
            : opportunity.status === 'NUEVA'
              ? 'Pasar a Para cotizar'
              : 'Marcar ganada'}
        </Button>
      ) : null}
      {opportunity.status === 'COTIZADA' || opportunity.status === 'GANADA' ? (
        <Button
          className='opportunity-detail__action'
          disabled={isMutating}
          onClick={() => {
            const fromStatus = opportunity.status as PipelineStatus
            const targetStatus = STAGE_BY_STATUS.get(fromStatus)?.previousStatus
            if (targetStatus) setPendingRegression({ fromStatus, targetStatus })
          }}
        >
          <Icon name='chevron-left' />
          Volver a{' '}
          {
            OPPORTUNITY_STATUS_LABELS[
              STAGE_BY_STATUS.get(opportunity.status as PipelineStatus)?.previousStatus ?? 'NUEVA'
            ]
          }
        </Button>
      ) : null}
      {opportunity.status === 'COTIZADA' ? (
        <Button className='opportunity-detail__action' onClick={() => openQuote('edit')}>
          <Icon name='pencil' />
          Editar cotización
        </Button>
      ) : null}
      <Button
        className='opportunity-detail__action opportunity-whatsapp-action'
        disabled={isLookingUpConversation || !hasComparablePhone(opportunity.customer.phone)}
        isLoading={isLookingUpConversation}
        onClick={() => void handleWhatsApp()}
      >
        <Icon name='whatsapp' />
        {isLookingUpConversation ? 'Abriendo WhatsApp…' : 'Iniciar WhatsApp'}
      </Button>
      {isEligibleForReopen(opportunity) ? (
        <Button
          className='opportunity-detail__action'
          onClick={() => setIsReopenConfirmationOpen(true)}
          variant='primary'
        >
          <Icon name='refresh' />
          Reabrir
        </Button>
      ) : null}
      {opportunity.status === 'NUEVA' ||
      opportunity.status === 'COTIZADA' ||
      opportunity.status === 'PARA_COTIZAR' ? (
        <Button
          className='opportunity-detail__action opportunity-detail__action--destructive'
          onClick={() => setLossOpportunity(opportunity)}
          variant='danger'
        >
          <Icon name='x-circle' />
          Marcar pérdida
        </Button>
      ) : null}
    </>
  ) : undefined
  const secondaryActions = opportunity ? (
    <Button
      className='!border-[var(--destructive-border)] !bg-[var(--destructive-subtle)] !text-[var(--destructive-text)] hover:!bg-[var(--destructive-subtle)] hover:brightness-95'
      disabled={isDeleting}
      onClick={() => {
        setDeleteError(null)
        setIsDeleteConfirmationOpen(true)
      }}
      variant='secondary'
    >
      <Icon name='trash' />
      Eliminar oportunidad
    </Button>
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
      contentClassName='opportunity-modal-panel'
      isOpen
      onClose={close}
      renderHeader={({ titleId }) => (
        <OpportunityDetailModalHeader
          opportunity={opportunity}
          returnAffordance={
            <AppLink
              className='inline-flex items-center gap-1 text-[var(--action-secondary)] outline-none hover:underline focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]'
              onClick={(event) => {
                event.preventDefault()
                close()
              }}
              to={{ kind: 'workspace', workspace: surface }}
            >
              <Icon className='size-3.5' name='chevron-left' />
              Volver a oportunidades
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
          {actionError && !pendingRegression && !isForwardConfirmationOpen ? (
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
            secondaryActions={secondaryActions}
          />
        </div>
      )}
      <ConfirmationDialog
        confirmLabel='Eliminar oportunidad'
        description='¿Seguro que querés eliminar esta oportunidad? Esta acción la quitará de las vistas comerciales.'
        error={deleteError}
        isOpen={isDeleteConfirmationOpen}
        isPending={isDeleting}
        onCancel={() => {
          if (!isDeleting) setIsDeleteConfirmationOpen(false)
        }}
        onConfirm={() => void handleDelete()}
        pendingLabel='Eliminando…'
        title='Eliminar oportunidad'
        variant='danger'
      >
        <p className='text-sm leading-6 text-[var(--text-secondary)]'>
          Esta acción realiza un borrado lógico y no elimina el cliente, las cotizaciones ni el
          historial de estados.
        </p>
      </ConfirmationDialog>
      <StageNoteConfirmation
        confirmLabel={
          pendingRegression
            ? `Volver a ${OPPORTUNITY_STATUS_LABELS[pendingRegression.targetStatus]}`
            : 'Confirmar retroceso'
        }
        description={
          pendingRegression
            ? `La oportunidad pasará de ${OPPORTUNITY_STATUS_LABELS[pendingRegression.fromStatus]} a ${OPPORTUNITY_STATUS_LABELS[pendingRegression.targetStatus]}.`
            : undefined
        }
        isOpen={pendingRegression !== null}
        isPending={isMutating}
        onCancel={() => {
          if (!isMutating) setPendingRegression(null)
        }}
        onConfirm={(note) => void confirmRegression(note)}
        error={actionError}
        pendingLabel='Actualizando…'
        title='Confirmar retroceso de etapa'
      >
        <p className='text-sm text-[var(--text-secondary)]'>
          El cambio quedará registrado con su fecha en el historial de la oportunidad.
        </p>
      </StageNoteConfirmation>
      <StageNoteConfirmation
        confirmLabel='Reabrir en Cotizada'
        description='La oportunidad volverá a Cotizada y conservará su historial de pérdida.'
        error={reopenError}
        isOpen={isReopenConfirmationOpen}
        isPending={isReopening}
        onCancel={() => {
          if (!isReopening) {
            setIsReopenConfirmationOpen(false)
            setReopenError(null)
          }
        }}
        onConfirm={(note) => void handleReopen(note)}
        pendingLabel='Reabriendo…'
        title='Reabrir oportunidad'
      >
        <p className='text-sm text-[var(--text-secondary)]'>
          El destino lo determina FAA CRM: Cotizada.
        </p>
      </StageNoteConfirmation>
      <StageNoteConfirmation
        confirmLabel={opportunity?.status === 'NUEVA' ? 'Pasar a Para cotizar' : 'Marcar ganada'}
        error={actionError}
        isOpen={isForwardConfirmationOpen}
        isPending={isMutating}
        onCancel={() => {
          if (!isMutating) setIsForwardConfirmationOpen(false)
        }}
        onConfirm={(note, province) => void move(note, province)}
        suggestProvince={
          opportunity?.status === 'COTIZADA' && !opportunity.customer.province?.trim()
        }
        pendingLabel='Guardando…'
        title='Confirmar cambio de etapa'
      >
        <p className='text-sm text-[var(--text-secondary)]'>
          El cambio y la nota se guardarán juntos en el historial del cliente.
        </p>
      </StageNoteConfirmation>
      <LossModal
        onClose={() => setLossOpportunity(null)}
        onConfirm={handleLoss}
        opportunity={lossOpportunity}
      />
    </Modal>
  )
}
