import { useEffect, useMemo, useRef, useState } from 'react'

import {
  type ApiSession,
  listPipelineOpportunities,
  moveOpportunityToNegotiation,
  quoteOpportunity,
  winOpportunity,
} from '../api/opportunities'
import { listActiveProducts } from '../api/products'
import { useAuth } from '../auth/AuthContext'
import {
  DEFAULT_PIPELINE_FILTERS,
  type PipelineFilters,
  projectPipeline,
} from '../pipeline/board-state'
import { canMoveTo, STAGE_BY_STATUS } from '../pipeline/config'
import { pipelineErrorMessage } from '../pipeline/errors'
import { PipelineBoard } from '../pipeline/PipelineBoard'
import { PipelineControls } from '../pipeline/PipelineControls'
import { QuoteModal } from '../pipeline/QuoteModal'
import type {
  OpportunitySummary,
  PipelineStatus,
  Product,
  QuoteProductInput,
} from '../pipeline/types'
import { navigateRoute } from '../routing/router'
import { Button } from '../shared/Button'
import { InlineFeedback } from '../shared/InlineFeedback'

function replaceOpportunity(
  opportunities: OpportunitySummary[],
  updatedOpportunity: OpportunitySummary,
): OpportunitySummary[] {
  return opportunities.map((opportunity) =>
    opportunity.id === updatedOpportunity.id ? updatedOpportunity : opportunity,
  )
}

function BoardSkeleton() {
  return (
    <div aria-label='Cargando pipeline' className='pipeline-board' role='status'>
      <div className='pipeline-board__grid'>
        {['Nueva', 'Cotizada', 'Negociación', 'Ganada'].map((label) => (
          <section className='pipeline-column' key={label}>
            <div className='pipeline-column__header'>
              <span className='ui-skeleton h-4 w-24' />
            </div>
            <div className='pipeline-column__cards'>
              <span className='ui-skeleton h-24 w-full' />
              <span className='ui-skeleton h-20 w-full' />
            </div>
          </section>
        ))}
      </div>
    </div>
  )
}

export function PipelinePage() {
  const { token, logout } = useAuth()
  const [opportunities, setOpportunities] = useState<OpportunitySummary[]>([])
  const [hasLoaded, setHasLoaded] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [operationError, setOperationError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [busyOpportunityIds, setBusyOpportunityIds] = useState<Set<number>>(new Set())
  const [quoteOpportunityId, setQuoteOpportunityId] = useState<number | null>(null)
  const [products, setProducts] = useState<Product[] | null>(null)
  const [isLoadingProducts, setIsLoadingProducts] = useState(false)
  const [productsError, setProductsError] = useState<string | null>(null)
  const [filters, setFilters] = useState<PipelineFilters>(DEFAULT_PIPELINE_FILTERS)
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [showStageAge, setShowStageAge] = useState(false)
  const [announcement, setAnnouncement] = useState('')
  const hasLoadedRef = useRef(false)

  const apiSession = useMemo<ApiSession>(
    () => ({ token: token ?? '', onUnauthorized: logout }),
    [logout, token],
  )

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(filters.search), 180)
    return () => window.clearTimeout(timer)
  }, [filters.search])

  useEffect(() => {
    void reloadKey
    const controller = new AbortController()
    setIsRefreshing(hasLoadedRef.current)
    setLoadError(null)
    listPipelineOpportunities({ ...apiSession, signal: controller.signal }, filters.source)
      .then(setOpportunities)
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setLoadError(pipelineErrorMessage(error, 'load'))
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          hasLoadedRef.current = true
          setHasLoaded(true)
          setIsRefreshing(false)
        }
      })
    return () => controller.abort()
  }, [apiSession, filters.source, reloadKey])

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

  const handleMove = async (opportunityId: number, targetStatus: PipelineStatus) => {
    const opportunity = findOpportunity(opportunityId)
    if (
      !opportunity ||
      !canMoveTo(opportunity.status as PipelineStatus, targetStatus) ||
      busyOpportunityIds.has(opportunityId)
    )
      return
    if (opportunity.status === 'NUEVA' && targetStatus === 'COTIZADA') {
      openQuoteModal(opportunityId)
      setAnnouncement(`Abriste la cotización para ${opportunity.customer.name}.`)
      return
    }

    setOperationError(null)
    setOpportunityBusy(opportunityId, true)
    const optimisticOpportunity: OpportunitySummary = {
      ...opportunity,
      status: targetStatus,
      current_status_entered_at: new Date().toISOString(),
    }
    setOpportunities((current) => replaceOpportunity(current, optimisticOpportunity))
    try {
      const updatedOpportunity =
        targetStatus === 'NEGOCIACION'
          ? await moveOpportunityToNegotiation(opportunityId, apiSession)
          : await winOpportunity(opportunityId, apiSession)
      setOpportunities((current) => replaceOpportunity(current, updatedOpportunity))
      setAnnouncement(
        `${opportunity.customer.name} pasó a ${STAGE_BY_STATUS.get(targetStatus)?.singularLabel}.`,
      )
    } catch (error) {
      setOpportunities((current) => replaceOpportunity(current, opportunity))
      setOperationError(pipelineErrorMessage(error, 'transition'))
      setAnnouncement(
        `No se pudo mover ${opportunity.customer.name}; se mantuvo en ${STAGE_BY_STATUS.get(opportunity.status as PipelineStatus)?.singularLabel}.`,
      )
    } finally {
      setOpportunityBusy(opportunityId, false)
    }
  }

  const handleQuote = async (quoteProducts: QuoteProductInput[]) => {
    const opportunity = quoteOpportunityId ? findOpportunity(quoteOpportunityId) : null
    if (!opportunity) throw new Error('La oportunidad ya no está disponible.')
    setOpportunityBusy(opportunity.id, true)
    try {
      const updatedOpportunity = await quoteOpportunity(opportunity.id, quoteProducts, apiSession)
      setOpportunities((current) => replaceOpportunity(current, updatedOpportunity))
      setQuoteOpportunityId(null)
      setAnnouncement(`${opportunity.customer.name} pasó a Cotizada.`)
    } catch (error) {
      throw new Error(pipelineErrorMessage(error, 'quote'))
    } finally {
      setOpportunityBusy(opportunity.id, false)
    }
  }

  const projectedOpportunities = useMemo(
    () => projectPipeline(opportunities, { ...filters, search: debouncedSearch }),
    [debouncedSearch, filters, opportunities],
  )
  const productOptions = useMemo(() => {
    const productsById = new Map<number, { id: number; name: string }>()
    opportunities.forEach((opportunity) => {
      opportunity.products.forEach((line) => {
        productsById.set(line.product.id, line.product)
      })
    })
    return [...productsById.values()].sort((left, right) =>
      left.name.localeCompare(right.name, 'es-AR'),
    )
  }, [opportunities])
  const quotedOpportunity = quoteOpportunityId ? findOpportunity(quoteOpportunityId) : null
  const noMatches =
    hasLoaded && !loadError && opportunities.length > 0 && projectedOpportunities.length === 0

  return (
    <section aria-labelledby='pipeline-workspace-title'>
      <div className='pipeline-page-heading'>
        <div>
          <h2 id='pipeline-workspace-title'>Pipeline</h2>
          <p>Oportunidades activas, ordenadas por evidencia comercial.</p>
        </div>
        <Button
          disabled={isRefreshing || busyOpportunityIds.size > 0}
          onClick={() => setReloadKey((current) => current + 1)}
        >
          {isRefreshing ? 'Actualizando…' : 'Actualizar'}
        </Button>
      </div>
      <PipelineControls
        filters={filters}
        onFiltersChange={setFilters}
        onReset={() => {
          setFilters(DEFAULT_PIPELINE_FILTERS)
          setShowStageAge(false)
        }}
        onShowStageAgeChange={setShowStageAge}
        productOptions={productOptions}
        showStageAge={showStageAge}
      />
      {operationError ? (
        <div className='mb-3'>
          <InlineFeedback message={operationError} onDismiss={() => setOperationError(null)} />
        </div>
      ) : null}
      {loadError && opportunities.length > 0 ? (
        <div className='mb-3'>
          <InlineFeedback message={loadError} onDismiss={() => setLoadError(null)} />
        </div>
      ) : null}
      {!hasLoaded && !loadError ? (
        <BoardSkeleton />
      ) : loadError && opportunities.length === 0 ? (
        <div className='ui-error-state' role='alert'>
          <p>{loadError}</p>
          <Button onClick={() => setReloadKey((current) => current + 1)}>Reintentar</Button>
        </div>
      ) : noMatches ? (
        <div className='ui-empty-state'>
          <h3>Sin resultados</h3>
          <p>Probá ajustar los filtros del Pipeline.</p>
          <Button
            onClick={() => {
              setFilters(DEFAULT_PIPELINE_FILTERS)
              setShowStageAge(false)
            }}
          >
            Limpiar filtros
          </Button>
        </div>
      ) : (
        <PipelineBoard
          busyOpportunityIds={busyOpportunityIds}
          onMove={(opportunityId, targetStatus) => void handleMove(opportunityId, targetStatus)}
          onOpenDetail={(opportunityId) =>
            navigateRoute(
              { kind: 'opportunity', opportunityId, surface: 'pipeline' },
              { origin: { kind: 'workspace', workspace: 'pipeline' } },
            )
          }
          opportunities={projectedOpportunities}
          showStageAge={showStageAge}
        />
      )}
      <p aria-atomic='true' aria-live='polite' className='sr-only'>
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
    </section>
  )
}
