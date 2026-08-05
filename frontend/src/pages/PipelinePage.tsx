import { useEffect, useMemo, useState } from 'react'

import {
  listPipelineOpportunities,
  loseOpportunity,
  moveOpportunityToNegotiation,
  quoteOpportunity,
  updateOpportunityQuoteProducts,
  winOpportunity,
  type ApiSession,
} from '../api/opportunities'
import { listActiveProducts } from '../api/products'
import { useAuth } from '../auth/AuthContext'
import { canMoveTo, STAGE_BY_STATUS } from '../pipeline/config'
import { pipelineErrorMessage } from '../pipeline/errors'
import { LossModal } from '../pipeline/LossModal'
import { PipelineBoard } from '../pipeline/PipelineBoard'
import { OpportunityDrawer } from '../pipeline/OpportunityDrawer'
import { QuoteModal } from '../pipeline/QuoteModal'
import type {
  LossReason,
  OpportunitySummary,
  OpportunityDetail,
  PipelineStatus,
  Product,
  QuoteProductInput,
} from '../pipeline/types'
import { InlineFeedback } from '../shared/InlineFeedback'
import { LoadingState } from '../shared/LoadingState'
import { Button } from '../shared/Button'

function replaceOpportunity(
  opportunities: OpportunitySummary[],
  updatedOpportunity: OpportunitySummary,
): OpportunitySummary[] {
  return opportunities.map((opportunity) =>
    opportunity.id === updatedOpportunity.id ? updatedOpportunity : opportunity,
  )
}

export function PipelinePage() {
  const { token, logout } = useAuth()
  const [opportunities, setOpportunities] = useState<OpportunitySummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [operationError, setOperationError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [busyOpportunityIds, setBusyOpportunityIds] = useState<Set<number>>(
    new Set(),
  )
  const [quoteOpportunityId, setQuoteOpportunityId] = useState<number | null>(
    null,
  )
  const [quoteMode, setQuoteMode] = useState<'create' | 'edit'>('create')
  const [quoteOpportunitySnapshot, setQuoteOpportunitySnapshot] =
    useState<OpportunitySummary | null>(null)
  const [lossOpportunityId, setLossOpportunityId] = useState<number | null>(
    null,
  )
  const [products, setProducts] = useState<Product[] | null>(null)
  const [isLoadingProducts, setIsLoadingProducts] = useState(false)
  const [productsError, setProductsError] = useState<string | null>(null)
  const [announcement, setAnnouncement] = useState('')
  const [selectedOpportunityId, setSelectedOpportunityId] = useState<number | null>(null)
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false)
  const [detailReloadKey, setDetailReloadKey] = useState(0)

  const apiSession = useMemo<ApiSession>(
    () => ({ token: token ?? '', onUnauthorized: logout }),
    [logout, token],
  )

  useEffect(() => {
    const controller = new AbortController()
    setIsLoading(true)
    setLoadError(null)

    listPipelineOpportunities({ ...apiSession, signal: controller.signal })
      .then(setOpportunities)
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setLoadError(pipelineErrorMessage(error, 'load'))
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false)
      })

    return () => controller.abort()
  }, [apiSession, reloadKey])

  const setOpportunityBusy = (opportunityId: number, isBusy: boolean) => {
    setBusyOpportunityIds((current) => {
      const next = new Set(current)
      if (isBusy) next.add(opportunityId)
      else next.delete(opportunityId)
      return next
    })
  }

  const findOpportunity = (opportunityId: number) =>
    opportunities.find((opportunity) => opportunity.id === opportunityId) ?? null

  const loadProducts = async () => {
    setIsLoadingProducts(true)
    setProductsError(null)
    try {
      const activeProducts = await listActiveProducts(apiSession)
      setProducts(activeProducts.filter((product) => product.is_active))
    } catch (error) {
      setProductsError(pipelineErrorMessage(error, 'quote'))
    } finally {
      setIsLoadingProducts(false)
    }
  }

  const openQuoteModal = (opportunityId: number) => {
    setOperationError(null)
    setQuoteMode('create')
    setQuoteOpportunitySnapshot(null)
    setQuoteOpportunityId(opportunityId)
    if (!products && !isLoadingProducts) void loadProducts()
  }

  const openEditQuoteModal = (
    opportunityId: number,
    detail: OpportunityDetail,
  ) => {
    setOperationError(null)
    setQuoteMode('edit')
    setQuoteOpportunitySnapshot(detail)
    setQuoteOpportunityId(opportunityId)
    if (!products && !isLoadingProducts) void loadProducts()
  }

  const handleMove = async (
    opportunityId: number,
    targetStatus: PipelineStatus,
  ) => {
    const opportunity = findOpportunity(opportunityId)
    if (
      !opportunity ||
      opportunity.status === 'PERDIDA' ||
      !canMoveTo(opportunity.status, targetStatus) ||
      busyOpportunityIds.has(opportunityId)
    ) {
      return
    }

    if (opportunity.status === 'NUEVA' && targetStatus === 'COTIZADA') {
      openQuoteModal(opportunityId)
      return
    }

    setOperationError(null)
    setOpportunityBusy(opportunityId, true)
    const optimisticOpportunity: OpportunitySummary = {
      ...opportunity,
      status: targetStatus,
      current_status_entered_at: new Date().toISOString(),
    }
    setOpportunities((current) =>
      replaceOpportunity(current, optimisticOpportunity),
    )

    try {
      const updatedOpportunity =
        targetStatus === 'NEGOCIACION'
          ? await moveOpportunityToNegotiation(opportunityId, apiSession)
          : await winOpportunity(opportunityId, apiSession)
      setOpportunities((current) =>
        replaceOpportunity(current, updatedOpportunity),
      )
      setAnnouncement(
        `${opportunity.customer.name} pasó a ${STAGE_BY_STATUS.get(targetStatus)?.singularLabel}.`,
      )
      setDetailReloadKey((current) => current + 1)
    } catch (error) {
      setOpportunities((current) => replaceOpportunity(current, opportunity))
      setOperationError(pipelineErrorMessage(error, 'transition'))
    } finally {
      setOpportunityBusy(opportunityId, false)
    }
  }

  const handleQuote = async (quoteProducts: QuoteProductInput[]) => {
    const opportunity = quoteOpportunityId
      ? findOpportunity(quoteOpportunityId)
      : null
    if (!opportunity) throw new Error('La oportunidad ya no está disponible.')

    setOpportunityBusy(opportunity.id, true)
    try {
      const updatedOpportunity =
        quoteMode === 'edit'
          ? await updateOpportunityQuoteProducts(
              opportunity.id,
              quoteProducts,
              apiSession,
            )
          : await quoteOpportunity(opportunity.id, quoteProducts, apiSession)
      setOpportunities((current) =>
        replaceOpportunity(current, updatedOpportunity),
      )
      setQuoteOpportunityId(null)
      setQuoteOpportunitySnapshot(null)
      setAnnouncement(
        quoteMode === 'edit'
          ? `Se actualizó la cotización de ${opportunity.customer.name}.`
          : `${opportunity.customer.name} pasó a Cotizada.`,
      )
      setDetailReloadKey((current) => current + 1)
    } catch (error) {
      throw new Error(pipelineErrorMessage(error, 'quote'))
    } finally {
      setOpportunityBusy(opportunity.id, false)
    }
  }

  const openLossModal = (opportunityId: number) => {
    setOperationError(null)
    setLossOpportunityId(opportunityId)
  }

  const openOpportunityDetail = (opportunityId: number) => {
    setSelectedOpportunityId(opportunityId)
    setIsDetailDrawerOpen(true)
  }

  const handleLoss = async (lossReason: LossReason) => {
    const opportunity = lossOpportunityId
      ? findOpportunity(lossOpportunityId)
      : null
    if (!opportunity) throw new Error('La oportunidad ya no está disponible.')

    setOpportunityBusy(opportunity.id, true)
    try {
      await loseOpportunity(opportunity.id, lossReason, apiSession)
      setOpportunities((current) =>
        current.filter((item) => item.id !== opportunity.id),
      )
      setLossOpportunityId(null)
      setSelectedOpportunityId(null)
      setIsDetailDrawerOpen(false)
      setAnnouncement(
        `${opportunity.customer.name} fue marcada como perdida y se quitó del pipeline.`,
      )
    } catch (error) {
      throw new Error(pipelineErrorMessage(error, 'lose'))
    } finally {
      setOpportunityBusy(opportunity.id, false)
    }
  }

  const quotedOpportunity =
    quoteOpportunitySnapshot ??
    (quoteOpportunityId ? findOpportunity(quoteOpportunityId) : null)
  const lostOpportunity = lossOpportunityId
    ? findOpportunity(lossOpportunityId)
    : null

  return (
    <section aria-labelledby="pipeline-workspace-title">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-950" id="pipeline-workspace-title">
            Tablero comercial
          </h2>
          <p className="mt-0.5 text-sm text-slate-600">
            Arrastrá una tarjeta para avanzar o abrila para ver el detalle.
          </p>
        </div>
        <Button
          disabled={isLoading || busyOpportunityIds.size > 0}
          onClick={() => setReloadKey((current) => current + 1)}
        >
          {isLoading ? 'Actualizando…' : 'Actualizar'}
        </Button>
      </div>

      {operationError ? (
        <div className="mb-4">
          <InlineFeedback
            message={operationError}
            onDismiss={() => setOperationError(null)}
          />
        </div>
      ) : null}

      {isLoading ? (
        <LoadingState label="Cargando pipeline…" />
      ) : loadError ? (
        <div className="ui-panel px-5 py-6">
          <InlineFeedback message={loadError} />
          <Button
            className="mt-4"
            onClick={() => setReloadKey((current) => current + 1)}
          >
            Reintentar
          </Button>
        </div>
      ) : (
        <PipelineBoard
          busyOpportunityIds={busyOpportunityIds}
          onMove={(opportunityId, targetStatus) => {
            void handleMove(opportunityId, targetStatus)
          }}
          onOpenDetail={openOpportunityDetail}
          opportunities={opportunities}
        />
      )}

      <p aria-atomic="true" aria-live="polite" className="sr-only">
        {announcement}
      </p>

      <QuoteModal
        isLoadingProducts={isLoadingProducts}
        mode={quoteMode}
        onClose={() => {
          setQuoteOpportunityId(null)
          setQuoteOpportunitySnapshot(null)
        }}
        onConfirm={handleQuote}
        onRetryProducts={() => void loadProducts()}
        opportunity={quotedOpportunity}
        products={products}
        productsError={productsError}
      />
      <LossModal
        onClose={() => setLossOpportunityId(null)}
        onConfirm={handleLoss}
        opportunity={lostOpportunity}
      />
      <OpportunityDrawer
        isOpen={isDetailDrawerOpen}
        isBusy={
          selectedOpportunityId !== null &&
          busyOpportunityIds.has(selectedOpportunityId)
        }
        onAfterClose={() => setSelectedOpportunityId(null)}
        onClose={() => setIsDetailDrawerOpen(false)}
        onEditQuote={openEditQuoteModal}
        onLose={openLossModal}
        onMove={(opportunityId, targetStatus) => {
          void handleMove(opportunityId, targetStatus)
        }}
        onQuote={openQuoteModal}
        opportunityId={selectedOpportunityId}
        reloadKey={detailReloadKey}
      />
    </section>
  )
}
