import { useEffect, useMemo, useRef, useState } from 'react'

import { ApiError } from '../api/client'
import { type ApiSession, getOpportunityDetail } from '../api/opportunities'
import { useAuth } from '../auth/AuthContext'
import { Button } from '../shared/Button'
import { Drawer } from '../shared/Drawer'
import { LoadingState } from '../shared/LoadingState'
import { STAGE_BY_STATUS } from './config'
import { OpportunityDetailContent } from './OpportunityDetailContent'
import type { OpportunityDetail, PipelineStatus } from './types'

export function OpportunityDrawer({
  opportunityId,
  isOpen,
  reloadKey,
  isBusy,
  onClose,
  onAfterClose,
  onMove,
  onQuote,
  onEditQuote,
  onLose,
}: {
  opportunityId: number | null
  isOpen: boolean
  reloadKey: number
  isBusy: boolean
  onClose: () => void
  onAfterClose: () => void
  onMove: (opportunityId: number, targetStatus: PipelineStatus) => void
  onQuote: (opportunityId: number) => void
  onEditQuote: (opportunityId: number, detail: OpportunityDetail) => void
  onLose: (opportunityId: number) => void
}) {
  const { token, logout } = useAuth()
  const [opportunity, setOpportunity] = useState<OpportunityDetail | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [loadError, setLoadError] = useState<'not-found' | 'request' | null>(null)
  const [retryKey, setRetryKey] = useState(0)
  const pendingActionRef = useRef<(() => void) | null>(null)
  const apiSession = useMemo<ApiSession>(
    () => ({ token: token ?? '', onUnauthorized: logout }),
    [logout, token],
  )

  useEffect(() => {
    void reloadKey
    void retryKey
    if (opportunityId === null) {
      setOpportunity(null)
      setLoadError(null)
      return
    }

    const controller = new AbortController()
    setIsLoading(true)
    setLoadError(null)

    getOpportunityDetail(opportunityId, { ...apiSession, signal: controller.signal })
      .then(setOpportunity)
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setLoadError(error instanceof ApiError && error.status === 404 ? 'not-found' : 'request')
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false)
      })

    return () => controller.abort()
  }, [apiSession, opportunityId, reloadKey, retryKey])

  const nextStatus =
    opportunity && opportunity.status !== 'PERDIDA'
      ? (STAGE_BY_STATUS.get(opportunity.status)?.nextStatus ?? null)
      : null

  const runAfterClose = (action: () => void) => {
    pendingActionRef.current = action
    onClose()
  }

  const handleAfterClose = () => {
    const pendingAction = pendingActionRef.current
    pendingActionRef.current = null
    onAfterClose()
    pendingAction?.()
  }

  const actions = opportunity ? (
    <>
      {opportunity.status === 'NUEVA' ? (
        <Button
          disabled={isBusy}
          onClick={() => runAfterClose(() => onQuote(opportunity.id))}
          variant='primary'
        >
          Cotizar
        </Button>
      ) : null}
      {opportunity.status === 'COTIZADA' || opportunity.status === 'NEGOCIACION' ? (
        <Button
          disabled={isBusy}
          onClick={() => runAfterClose(() => onEditQuote(opportunity.id, opportunity))}
        >
          Editar cotización
        </Button>
      ) : null}
      {nextStatus && opportunity.status !== 'NUEVA' ? (
        <Button
          disabled={isBusy}
          onClick={() => onMove(opportunity.id, nextStatus)}
          variant='primary'
        >
          {opportunity.status === 'COTIZADA' ? 'Pasar a negociación' : 'Marcar ganada'}
        </Button>
      ) : null}
      {nextStatus ? (
        <Button
          className='text-rose-700 hover:bg-rose-50 hover:text-rose-900'
          disabled={isBusy}
          onClick={() => runAfterClose(() => onLose(opportunity.id))}
          variant='ghost'
        >
          Marcar perdida
        </Button>
      ) : null}
    </>
  ) : null

  return (
    <Drawer
      closeDisabled={isBusy}
      description='Información comercial completa'
      isOpen={isOpen}
      onAfterClose={handleAfterClose}
      onClose={onClose}
      title='Detalle de oportunidad'
    >
      {isLoading && !opportunity ? (
        <LoadingState label='Cargando oportunidad…' />
      ) : loadError ? (
        <div
          className='m-4 ui-panel px-4 py-5'
          role={loadError === 'request' ? 'alert' : undefined}
        >
          <h3 className='text-base font-semibold text-slate-950'>
            {loadError === 'not-found'
              ? 'Oportunidad no encontrada'
              : 'No pudimos cargar la oportunidad'}
          </h3>
          <p className='mt-1 text-sm text-slate-600'>
            {loadError === 'not-found'
              ? 'La oportunidad ya no está disponible.'
              : 'Revisá tu conexión e intentá nuevamente.'}
          </p>
          {loadError === 'request' ? (
            <Button className='mt-4' onClick={() => setRetryKey((current) => current + 1)}>
              Reintentar
            </Button>
          ) : null}
        </div>
      ) : opportunity ? (
        <OpportunityDetailContent actions={actions} layout='drawer' opportunity={opportunity} />
      ) : null}
    </Drawer>
  )
}
