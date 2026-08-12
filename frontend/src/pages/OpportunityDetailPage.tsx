import { useEffect, useMemo, useState } from 'react'

import { ApiError } from '../api/client'
import { type ApiSession, getOpportunityDetail } from '../api/opportunities'
import { useAuth } from '../auth/AuthContext'
import { OpportunityDetailContent } from '../pipeline/OpportunityDetailContent'
import type { OpportunityDetail } from '../pipeline/types'
import { AppLink } from '../routing/router'
import { Button } from '../shared/Button'
import { LoadingState } from '../shared/LoadingState'

function BackToPipelineLink() {
  return (
    <AppLink
      className='ui-pressable inline-flex min-h-11 items-center gap-2 rounded-[4px] px-2 text-sm font-semibold text-slate-600 outline-none hover:bg-white hover:text-slate-950 focus-visible:ring-2 focus-visible:ring-slate-500'
      to='/pipeline'
    >
      <svg aria-hidden='true' className='size-4' fill='none' viewBox='0 0 20 20'>
        <path
          d='m12.5 4.5-5.5 5.5 5.5 5.5'
          stroke='currentColor'
          strokeLinecap='round'
          strokeLinejoin='round'
          strokeWidth='1.8'
        />
      </svg>
      Volver al Pipeline
    </AppLink>
  )
}

function DetailError({ notFound, onRetry }: { notFound: boolean; onRetry: () => void }) {
  return (
    <section aria-labelledby='opportunity-error-title' className='max-w-3xl'>
      <BackToPipelineLink />
      <div className='ui-panel mt-3 px-5 py-6'>
        <h2 className='text-lg font-semibold text-slate-950' id='opportunity-error-title'>
          {notFound ? 'Oportunidad no encontrada' : 'No pudimos cargar la oportunidad'}
        </h2>
        <p className='mt-2 text-sm leading-6 text-slate-600'>
          {notFound
            ? 'La oportunidad no existe, fue eliminada o ya no está disponible.'
            : 'Revisá tu conexión e intentá nuevamente.'}
        </p>
        {!notFound ? (
          <Button className='mt-4' onClick={onRetry}>
            Reintentar
          </Button>
        ) : null}
      </div>
    </section>
  )
}

export function OpportunityDetailPage({ opportunityId }: { opportunityId: number }) {
  const { token, logout } = useAuth()
  const [opportunity, setOpportunity] = useState<OpportunityDetail | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<'not-found' | 'request' | null>(null)
  const [reloadKey, setReloadKey] = useState(0)

  const apiSession = useMemo<ApiSession>(
    () => ({ token: token ?? '', onUnauthorized: logout }),
    [logout, token],
  )

  useEffect(() => {
    void reloadKey
    const controller = new AbortController()
    setOpportunity(null)
    setLoadError(null)
    setIsLoading(true)

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
  }, [apiSession, opportunityId, reloadKey])

  if (isLoading) return <LoadingState label='Cargando oportunidad…' />

  if (loadError || !opportunity) {
    return (
      <DetailError
        notFound={loadError === 'not-found'}
        onRetry={() => setReloadKey((current) => current + 1)}
      />
    )
  }

  return (
    <div className='mx-auto max-w-6xl'>
      <BackToPipelineLink />
      <div className='mt-3'>
        <OpportunityDetailContent opportunity={opportunity} />
      </div>
    </div>
  )
}
