import { useEffect, useMemo, useState } from 'react'

import { ApiError } from '../api/client'
import { type ApiSession, getOpportunityDetail } from '../api/opportunities'
import { useAuth } from '../auth/AuthContext'
import { OpportunityDetailContent } from '../pipeline/OpportunityDetailContent'
import type { OpportunityDetail } from '../pipeline/types'
import { AppLink, navigateRoute, navigateToHistoryOrigin } from '../routing/router'
import { Button } from '../shared/Button'
import { LoadingState } from '../shared/LoadingState'
import { Modal } from '../shared/Modal'

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
          {error !== 'not-found' ? (
            <Button className='mt-4' onClick={() => setKey((value) => value + 1)}>
              Reintentar
            </Button>
          ) : null}
        </div>
      ) : (
        <div className='max-h-[calc(100dvh-10rem)] overflow-y-auto p-4'>
          <OpportunityDetailContent opportunity={opportunity} />
        </div>
      )}
    </Modal>
  )
}
