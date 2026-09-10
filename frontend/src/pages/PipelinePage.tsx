import { useEffect, useMemo, useReducer, useRef, useState } from 'react'

import {
  type ApiSession,
  listOpportunityStage,
  moveOpportunityToNegotiation,
  quoteOpportunity,
  winOpportunity,
} from '../api/opportunities'
import { useAuth } from '../auth/AuthContext'
import {
  DEFAULT_PIPELINE_FILTERS,
  type PipelineFilters,
  projectPipeline,
} from '../pipeline/board-state'
import { canMoveTo, PIPELINE_STAGES, STAGE_BY_STATUS } from '../pipeline/config'
import { pipelineErrorMessage } from '../pipeline/errors'
import { ManualOpportunityModal } from '../pipeline/ManualOpportunityModal'
import {
  EMPTY_OPPORTUNITY_WORKSPACE_STATE,
  opportunityWorkspaceReducer,
  workspaceOpportunities,
} from '../pipeline/opportunity-workspace-state'
import { PipelineBoard } from '../pipeline/PipelineBoard'
import { PipelineControls } from '../pipeline/PipelineControls'
import { QuoteModal } from '../pipeline/QuoteModal'
import type { OpportunitySummary, PipelineStatus, QuoteProductInput } from '../pipeline/types'
import { useActiveProductCatalog } from '../pipeline/useActiveProductCatalog'
import { navigateRoute } from '../routing/router'
import { Button } from '../shared/Button'
import { Icon } from '../shared/Icon'
import { EmptyState, InlineFeedback } from '../shared/StatusStates'
import { OpportunityDetailPage } from './OpportunityDetailPage'

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

export function PipelinePage({ selectedOpportunityId }: { selectedOpportunityId?: number }) {
  const { token, logout, user } = useAuth()
  const [workspace, dispatch] = useReducer(
    opportunityWorkspaceReducer,
    EMPTY_OPPORTUNITY_WORKSPACE_STATE,
  )
  const [hasLoaded, setHasLoaded] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [operationError, setOperationError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [busyOpportunityIds, setBusyOpportunityIds] = useState<Set<number>>(new Set())
  const [quoteOpportunityId, setQuoteOpportunityId] = useState<number | null>(null)
  const [filters, setFilters] = useState<PipelineFilters>(DEFAULT_PIPELINE_FILTERS)
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [showStageAge, setShowStageAge] = useState(false)
  const [announcement, setAnnouncement] = useState('')
  const [isManualCreationOpen, setIsManualCreationOpen] = useState(false)
  const [hiddenCreatedOpportunity, setHiddenCreatedOpportunity] =
    useState<OpportunitySummary | null>(null)
  const hasLoadedRef = useRef(false)
  const requestVersionRef = useRef(0)
  const wonRequestVersionRef = useRef(0)
  const wonReconciliationControllerRef = useRef<AbortController | null>(null)
  const mutationGenerationRef = useRef<Record<number, number>>({})
  const manualCreationTriggerRef = useRef<HTMLButtonElement>(null)

  const apiSession = useMemo<ApiSession>(
    () => ({ token: token ?? '', onUnauthorized: logout }),
    [logout, token],
  )
  const catalog = useActiveProductCatalog(apiSession)
  const opportunities = useMemo(() => workspaceOpportunities(workspace), [workspace])
  const wonOpportunities = useMemo(
    () => opportunities.filter((opportunity) => opportunity.status === 'GANADA'),
    [opportunities],
  )

  useEffect(() => {
    if (wonOpportunities.length === 0) return
    let timer: number | null = null
    const reconcileWon = () => {
      wonReconciliationControllerRef.current?.abort()
      const controller = new AbortController()
      wonReconciliationControllerRef.current = controller
      const requestVersion = wonRequestVersionRef.current + 1
      wonRequestVersionRef.current = requestVersion
      const generations = { ...mutationGenerationRef.current }
      void listOpportunityStage('GANADA', filters.source, {
        ...apiSession,
        signal: controller.signal,
      })
        .then((items) => {
          if (wonRequestVersionRef.current !== requestVersion) return
          const protectedOpportunityIds = Object.entries(mutationGenerationRef.current)
            .filter(([id, generation]) => generation > (generations[Number(id)] ?? 0))
            .map(([id]) => Number(id))
          dispatch({
            type: 'replace-stage',
            status: 'GANADA',
            opportunities: items,
            protectedOpportunityIds,
          })
        })
        .catch(() => setLoadError('No pudimos reconciliar la columna Ganada.'))
    }
    const expireAndReconcile = () => {
      const now = Date.now()
      for (const opportunity of wonOpportunities) {
        if (Date.parse(opportunity.current_status_entered_at) + 30 * 86_400_000 <= now)
          dispatch({ type: 'remove', opportunityId: opportunity.id })
      }
      reconcileWon()
    }
    const earliest = Math.min(
      ...wonOpportunities.map(
        (opportunity) => Date.parse(opportunity.current_status_entered_at) + 30 * 86_400_000,
      ),
    )
    const schedule = () => {
      const remaining = earliest - Date.now()
      if (remaining <= 0) {
        expireAndReconcile()
        return
      }
      timer = window.setTimeout(schedule, Math.min(remaining, 2_147_000_000))
    }
    schedule()
    const recover = () => {
      if (document.visibilityState === 'visible') reconcileWon()
    }
    window.addEventListener('focus', recover)
    document.addEventListener('visibilitychange', recover)
    return () => {
      if (timer !== null) window.clearTimeout(timer)
      window.removeEventListener('focus', recover)
      document.removeEventListener('visibilitychange', recover)
    }
  }, [apiSession, filters.source, wonOpportunities])

  useEffect(
    () => () => {
      wonReconciliationControllerRef.current?.abort()
      wonRequestVersionRef.current += 1
    },
    [],
  )

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(filters.search), 180)
    return () => window.clearTimeout(timer)
  }, [filters.search])

  useEffect(() => {
    void reloadKey
    const controller = new AbortController()
    const requestVersion = requestVersionRef.current + 1
    requestVersionRef.current = requestVersion
    const mutationGenerationsAtStart = { ...mutationGenerationRef.current }
    setIsRefreshing(hasLoadedRef.current)
    setLoadError(null)
    const requestSession = { ...apiSession, signal: controller.signal }
    void Promise.allSettled(
      PIPELINE_STAGES.map((stage) =>
        listOpportunityStage(stage.status, filters.source, requestSession),
      ),
    )
      .then((results) => {
        if (controller.signal.aborted || requestVersionRef.current !== requestVersion) return
        const failedStages: string[] = []
        results.forEach((result, index) => {
          const stage = PIPELINE_STAGES[index]
          if (!stage) return
          if (result.status === 'fulfilled') {
            const protectedOpportunityIds = Object.entries(mutationGenerationRef.current)
              .filter(
                ([id, generation]) => generation > (mutationGenerationsAtStart[Number(id)] ?? 0),
              )
              .map(([id]) => Number(id))
            dispatch({
              type: 'replace-stage',
              status: stage.status,
              opportunities: result.value,
              protectedOpportunityIds,
            })
          } else {
            failedStages.push(stage.label)
          }
        })
        if (failedStages.length > 0) {
          setLoadError(
            hasLoadedRef.current
              ? `La actualización fue parcial. No pudimos actualizar: ${failedStages.join(', ')}.`
              : 'No pudimos conectar con el servidor. Revisá tu conexión e intentá nuevamente.',
          )
        }
      })
      .finally(() => {
        if (!controller.signal.aborted && requestVersionRef.current === requestVersion) {
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

  const findOpportunity = (opportunityId: number) => workspace.summariesById[opportunityId] ?? null

  const openQuoteModal = (opportunityId: number) => {
    setOperationError(null)
    setQuoteOpportunityId(opportunityId)
    if (!catalog.products && !catalog.isLoading) void catalog.load().catch(() => undefined)
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
    const generation = (mutationGenerationRef.current[opportunityId] ?? 0) + 1
    mutationGenerationRef.current[opportunityId] = generation
    dispatch({ type: 'start-mutation', opportunityId })
    dispatch({ type: 'upsert', opportunity: optimisticOpportunity })
    try {
      const updatedOpportunity =
        targetStatus === 'NEGOCIACION'
          ? await moveOpportunityToNegotiation(opportunityId, apiSession)
          : await winOpportunity(opportunityId, apiSession)
      if (mutationGenerationRef.current[opportunityId] === generation)
        dispatch({ type: 'upsert', opportunity: updatedOpportunity })
      setAnnouncement(
        `${opportunity.customer.name} pasó a ${STAGE_BY_STATUS.get(targetStatus)?.singularLabel}.`,
      )
    } catch (error) {
      if (mutationGenerationRef.current[opportunityId] === generation)
        dispatch({ type: 'upsert', opportunity })
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
    mutationGenerationRef.current[opportunity.id] =
      (mutationGenerationRef.current[opportunity.id] ?? 0) + 1
    dispatch({ type: 'start-mutation', opportunityId: opportunity.id })
    setOpportunityBusy(opportunity.id, true)
    try {
      const updatedOpportunity = await quoteOpportunity(opportunity.id, quoteProducts, apiSession)
      dispatch({ type: 'upsert', opportunity: updatedOpportunity })
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

  const handleManualCreated = (opportunity: OpportunitySummary) => {
    mutationGenerationRef.current[opportunity.id] =
      (mutationGenerationRef.current[opportunity.id] ?? 0) + 1
    dispatch({ type: 'upsert', opportunity })
    const isHidden = projectPipeline([opportunity], filters).length === 0
    setHiddenCreatedOpportunity(isHidden ? opportunity : null)
    setIsManualCreationOpen(false)
    setAnnouncement(
      isHidden
        ? 'Oportunidad creada. Los filtros actuales la están ocultando.'
        : `${opportunity.customer.name} fue creada en Nueva.`,
    )
  }

  const revealCreatedOpportunity = () => {
    if (!hiddenCreatedOpportunity) return
    setFilters((current) => {
      const matchesSearch =
        projectPipeline([hiddenCreatedOpportunity], {
          ...current,
          source: 'ALL',
          productId: 'ALL',
        }).length > 0
      return {
        ...current,
        search: matchesSearch ? current.search : '',
        source:
          current.source !== 'ALL' && current.source !== hiddenCreatedOpportunity.source
            ? 'ALL'
            : current.source,
        productId:
          current.productId !== 'ALL' &&
          !hiddenCreatedOpportunity.products.some(
            (line) => String(line.product.id) === current.productId,
          )
            ? 'ALL'
            : current.productId,
      }
    })
    setHiddenCreatedOpportunity(null)
    setAnnouncement(`${hiddenCreatedOpportunity.customer.name} está visible en Nueva.`)
  }

  return (
    <section aria-label='Pipeline' className='pipeline-page'>
      <PipelineControls
        action={
          <div className='pipeline-controls__actions'>
            <Button
              className='pipeline-control-button'
              onClick={() => setIsManualCreationOpen(true)}
              ref={manualCreationTriggerRef}
              size='compact'
              variant='primary'
            >
              <span aria-hidden='true' className='text-base leading-none'>
                +
              </span>
              Nueva oportunidad
            </Button>
            <Button
              className='pipeline-control-button'
              disabled={isRefreshing || busyOpportunityIds.size > 0}
              onClick={() => setReloadKey((current) => current + 1)}
              size='compact'
              variant='ghost'
            >
              <Icon
                className={
                  isRefreshing ? 'size-4 animate-spin motion-reduce:animate-none' : 'size-4'
                }
                name='refresh'
              />
              {isRefreshing ? 'Actualizando…' : 'Actualizar'}
            </Button>
          </div>
        }
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
      {hiddenCreatedOpportunity ? (
        <div className='pipeline-created-hidden' role='status'>
          <span>
            <Icon className='pipeline-created-hidden__icon' name='check' />
            Oportunidad creada. Los filtros actuales la están ocultando.
          </span>
          <Button onClick={revealCreatedOpportunity} size='compact' variant='secondary'>
            Ver en Nueva
          </Button>
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
        <EmptyState
          action={
            <Button
              onClick={() => {
                setFilters(DEFAULT_PIPELINE_FILTERS)
                setShowStageAge(false)
              }}
            >
              Limpiar filtros
            </Button>
          }
          description='Probá ajustar los filtros del Pipeline.'
          icon='search'
          size='small'
          title='Sin resultados'
        />
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
          selectedOpportunityId={selectedOpportunityId}
          opportunities={projectedOpportunities}
          showStageAge={showStageAge}
        />
      )}
      <p aria-atomic='true' aria-live='polite' className='sr-only'>
        {announcement}
      </p>
      <QuoteModal
        isLoadingProducts={catalog.isLoading}
        onClose={() => setQuoteOpportunityId(null)}
        onConfirm={handleQuote}
        onRetryProducts={() => void catalog.retry().catch(() => undefined)}
        opportunity={quotedOpportunity}
        products={catalog.products}
        productsError={catalog.error}
      />
      {user ? (
        <ManualOpportunityModal
          apiSession={apiSession}
          isOpen={isManualCreationOpen}
          onClose={() => setIsManualCreationOpen(false)}
          onCreated={handleManualCreated}
          returnFocusTo={manualCreationTriggerRef.current}
          user={user}
        />
      ) : null}
      {selectedOpportunityId ? (
        <OpportunityDetailPage
          catalog={catalog}
          cachedOpportunity={workspace.detailsById[selectedOpportunityId]}
          onOpportunityUpdated={(opportunity) => {
            mutationGenerationRef.current[opportunity.id] =
              (mutationGenerationRef.current[opportunity.id] ?? 0) + 1
            dispatch({ type: 'cache-detail', opportunity })
          }}
          opportunityId={selectedOpportunityId}
          surface='pipeline'
        />
      ) : null}
    </section>
  )
}
