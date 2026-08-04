import { useEffect, useMemo, useState } from 'react'

import {
  listPipelineOpportunities,
  loseOpportunity,
  moveOpportunityToNegotiation,
  quoteOpportunity,
  winOpportunity,
  type ApiSession,
} from '../api/opportunities'
import { listActiveProducts } from '../api/products'
import { useAuth } from '../auth/AuthContext'
import { canMoveTo, STAGE_BY_STATUS } from '../pipeline/config'
import { pipelineErrorMessage } from '../pipeline/errors'
import { LossModal } from '../pipeline/LossModal'
import { PipelineBoard } from '../pipeline/PipelineBoard'
import { QuoteModal } from '../pipeline/QuoteModal'
import type {
  LossReason,
  OpportunitySummary,
  PipelineStatus,
  Product,
  QuoteProductInput,
} from '../pipeline/types'
import { InlineFeedback } from '../shared/InlineFeedback'
import { LoadingState } from '../shared/LoadingState'

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
  const [lossOpportunityId, setLossOpportunityId] = useState<number | null>(
    null,
  )
  const [products, setProducts] = useState<Product[] | null>(null)
  const [isLoadingProducts, setIsLoadingProducts] = useState(false)
  const [productsError, setProductsError] = useState<string | null>(null)
  const [announcement, setAnnouncement] = useState('')

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
      const updatedOpportunity = await quoteOpportunity(
        opportunity.id,
        quoteProducts,
        apiSession,
      )
      setOpportunities((current) =>
        replaceOpportunity(current, updatedOpportunity),
      )
      setQuoteOpportunityId(null)
      setAnnouncement(`${opportunity.customer.name} pasó a Cotizada.`)
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
      setAnnouncement(
        `${opportunity.customer.name} fue marcada como perdida y se quitó del pipeline.`,
      )
    } catch (error) {
      throw new Error(pipelineErrorMessage(error, 'lose'))
    } finally {
      setOpportunityBusy(opportunity.id, false)
    }
  }

  const quotedOpportunity = quoteOpportunityId
    ? findOpportunity(quoteOpportunityId)
    : null
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
          <p className="mt-1 text-sm text-slate-600">
            Arrastrá cada oportunidad a su siguiente etapa o usá su acción “Mover a”.
          </p>
        </div>
        <button
          className="min-h-11 border border-slate-300 bg-white px-3.5 py-2 text-sm font-semibold text-slate-700 outline-none transition-colors duration-150 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-amber-500 disabled:cursor-wait disabled:opacity-50 motion-reduce:transition-none"
          disabled={isLoading || busyOpportunityIds.size > 0}
          onClick={() => setReloadKey((current) => current + 1)}
          type="button"
        >
          {isLoading ? 'Actualizando…' : 'Actualizar'}
        </button>
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
        <div className="border border-slate-200 bg-white px-5 py-6">
          <InlineFeedback message={loadError} />
          <button
            className="mt-4 min-h-11 border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-amber-500"
            onClick={() => setReloadKey((current) => current + 1)}
            type="button"
          >
            Reintentar
          </button>
        </div>
      ) : (
        <PipelineBoard
          busyOpportunityIds={busyOpportunityIds}
          onLose={openLossModal}
          onMove={(opportunityId, targetStatus) => {
            void handleMove(opportunityId, targetStatus)
          }}
          opportunities={opportunities}
        />
      )}

      <p aria-atomic="true" aria-live="polite" className="sr-only">
        {announcement}
      </p>

      <QuoteModal
        isLoadingProducts={isLoadingProducts}
        onClose={() => setQuoteOpportunityId(null)}
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
    </section>
  )
}
