import { useState } from 'react'

import type { CustomerDetail } from '../customers/types'
import {
  OPPORTUNITY_STATUS_LABELS,
  OPPORTUNITY_STATUS_TONES,
  SOURCE_LABELS,
} from '../pipeline/config'
import type { OpportunityDetail } from '../pipeline/types'
import { AppLink } from '../routing/router'
import { Badge } from '../shared/Badge'
import { Button } from '../shared/Button'
import { formatQuantityKg } from '../shared/formatters'
import { LoadingState } from '../shared/LoadingState'
import { Modal } from '../shared/Modal'
import type { WhatsAppConversationDetail, WhatsAppOpportunitySummary } from './types'

type LinkConfirmation =
  | { kind: 'link'; opportunity: WhatsAppOpportunitySummary }
  | { kind: 'unlink'; opportunity: WhatsAppOpportunitySummary }

function ContextField({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className='text-[0.6875rem] font-bold uppercase tracking-wide text-slate-500'>{label}</dt>
      <dd className='mt-0.5 break-words text-sm text-slate-800'>{value || 'No informado'}</dd>
    </div>
  )
}

function OpportunityCard({
  opportunity,
  detail,
  action,
  conversationId,
}: {
  opportunity: WhatsAppOpportunitySummary
  detail: OpportunityDetail | null
  action?: React.ReactNode
  conversationId: number
}) {
  return (
    <article className='rounded-[4px] border border-slate-200 bg-slate-50 px-3 py-3'>
      <div className='flex flex-wrap items-start justify-between gap-2'>
        <div>
          <p className='text-xs font-bold uppercase tracking-wide text-slate-500'>
            Oportunidad #{opportunity.id}
          </p>
          <div className='mt-1.5 flex flex-wrap gap-1.5'>
            <Badge tone={OPPORTUNITY_STATUS_TONES[opportunity.status]}>
              {OPPORTUNITY_STATUS_LABELS[opportunity.status]}
            </Badge>
            <Badge>{SOURCE_LABELS[opportunity.source]}</Badge>
          </div>
        </div>
        {action}
      </div>
      {detail ? (
        <div className='mt-3 border-t border-slate-200 pt-3'>
          <p className='text-xs font-semibold text-slate-700'>Productos y volumen</p>
          {detail.products.length > 0 ? (
            <ul className='mt-1.5 space-y-1 text-xs text-slate-600'>
              {detail.products.map((quoted) => (
                <li className='flex justify-between gap-3' key={quoted.product.id}>
                  <span>{quoted.product.name}</span>
                  <span className='shrink-0 font-semibold text-slate-800'>
                    {formatQuantityKg(quoted.quantity_kg)}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className='mt-1 text-xs text-slate-500'>Sin cotización registrada.</p>
          )}
        </div>
      ) : null}
      <AppLink
        className='mt-3 inline-flex min-h-11 items-center text-xs font-semibold text-slate-700 underline decoration-slate-300 underline-offset-4 outline-none hover:text-slate-950 focus-visible:ring-2 focus-visible:ring-slate-500'
        origin={{ kind: 'conversation', conversationId }}
        to={{
          kind: 'opportunity',
          opportunityId: opportunity.id,
          surface: opportunity.status === 'PERDIDA' ? 'lost' : 'pipeline',
        }}
      >
        Abrir oportunidad
      </AppLink>
    </article>
  )
}

export function CrmContextPanel({
  conversation,
  customerDetail,
  opportunityDetail,
  status,
  error,
  isLinking,
  linkError,
  headingId = 'whatsapp-context-title',
  onRetryContext,
  onUpdateLink,
}: {
  conversation: WhatsAppConversationDetail
  customerDetail: CustomerDetail | null
  opportunityDetail: OpportunityDetail | null
  status: 'idle' | 'loading' | 'ready' | 'error'
  error: string | null
  isLinking: boolean
  linkError: string | null
  headingId?: string
  onRetryContext: () => void
  onUpdateLink: (opportunityId: number | null) => Promise<void>
}) {
  const [confirmation, setConfirmation] = useState<LinkConfirmation | null>(null)
  const customer = conversation.customer
  const active = conversation.active_opportunity
  const confirmationTitle =
    confirmation?.kind === 'unlink'
      ? 'Desvincular oportunidad'
      : active
        ? 'Reemplazar oportunidad activa'
        : 'Vincular oportunidad'

  const confirm = async () => {
    if (!confirmation) return
    await onUpdateLink(confirmation.kind === 'link' ? confirmation.opportunity.id : null)
    setConfirmation(null)
  }

  return (
    <aside aria-labelledby={headingId} className='flex min-h-0 flex-col bg-white'>
      <header className='shrink-0 border-b border-slate-200 px-4 py-3'>
        <h2 className='text-sm font-semibold text-slate-950' id={headingId}>
          Contexto CRM
        </h2>
        <p className='mt-0.5 text-xs text-slate-500'>Información para responder mejor</p>
      </header>
      <div className='min-h-0 flex-1 overflow-y-auto px-4 py-4'>
        {conversation.resolution_status === 'NEEDS_REVIEW' ? (
          <div className='rounded-[4px] border border-rose-200 bg-rose-50 px-3 py-3' role='status'>
            <p className='text-sm font-semibold text-rose-900'>Identidad pendiente</p>
            <p className='mt-1 text-xs leading-5 text-rose-800'>
              El teléfono coincide de forma ambigua. No se puede responder ni vincular una
              oportunidad hasta resolverlo.
            </p>
          </div>
        ) : null}

        <section aria-labelledby='context-customer-title' className='mt-1'>
          <div className='flex items-center justify-between gap-3'>
            <h3 className='text-sm font-semibold text-slate-900' id='context-customer-title'>
              Cliente
            </h3>
            {customer?.is_available ? (
              <AppLink
                className='inline-flex min-h-11 items-center text-xs font-semibold text-slate-600 underline decoration-slate-300 underline-offset-4 outline-none hover:text-slate-950 focus-visible:ring-2 focus-visible:ring-slate-500'
                origin={{ kind: 'conversation', conversationId: conversation.id }}
                to={{ kind: 'customer', customerId: customer.id }}
              >
                Abrir ficha
              </AppLink>
            ) : null}
          </div>
          <dl className='mt-2 grid gap-3'>
            <ContextField label='Nombre' value={customer?.name ?? conversation.display_name} />
            <ContextField label='Empresa' value={customer?.company ?? null} />
            <ContextField label='Teléfono' value={customer?.phone ?? conversation.external_phone} />
            <ContextField label='Email' value={customerDetail?.email ?? null} />
            <ContextField label='Provincia' value={customer?.province ?? null} />
          </dl>
          {status === 'loading' ? <LoadingState label='Completando contexto…' /> : null}
          {error ? (
            <div className='mt-2'>
              <p className='text-xs font-medium text-rose-700' role='status'>
                {error}
              </p>
              <Button className='mt-2' onClick={onRetryContext} size='compact' variant='ghost'>
                Reintentar contexto
              </Button>
            </div>
          ) : null}
        </section>

        <section
          aria-labelledby='context-opportunity-title'
          className='mt-5 border-t border-slate-200 pt-4'
        >
          <h3 className='text-sm font-semibold text-slate-900' id='context-opportunity-title'>
            Oportunidad comercial
          </h3>
          {linkError ? (
            <p className='mt-2 text-xs font-medium text-rose-700' role='alert'>
              {linkError}
            </p>
          ) : null}
          {active ? (
            <div className='mt-3'>
              <OpportunityCard
                action={
                  <Button
                    disabled={isLinking || !active.is_available}
                    onClick={() => setConfirmation({ kind: 'unlink', opportunity: active })}
                    size='compact'
                    variant='ghost'
                  >
                    Desvincular
                  </Button>
                }
                detail={opportunityDetail}
                conversationId={conversation.id}
                opportunity={active}
              />
            </div>
          ) : (
            <p className='mt-2 text-xs leading-5 text-slate-500'>
              No hay una oportunidad activa vinculada. El CRM no crea una automáticamente.
            </p>
          )}

          {conversation.opportunity_suggestions.length > 0 ? (
            <div className='mt-4'>
              <p className='text-xs font-semibold text-slate-700'>
                {active ? 'Otras oportunidades abiertas' : 'Sugerencias abiertas'}
              </p>
              <ul className='mt-2 space-y-2'>
                {conversation.opportunity_suggestions.map((suggestion) => (
                  <li
                    className='flex items-center justify-between gap-2 rounded-[4px] border border-slate-200 px-3 py-2'
                    key={suggestion.id}
                  >
                    <span className='min-w-0'>
                      <span className='block text-xs font-semibold text-slate-800'>
                        Oportunidad #{suggestion.id}
                      </span>
                      <span className='text-[0.6875rem] text-slate-500'>
                        {OPPORTUNITY_STATUS_LABELS[suggestion.status]}
                      </span>
                    </span>
                    <Button
                      disabled={isLinking || !suggestion.is_available}
                      onClick={() => setConfirmation({ kind: 'link', opportunity: suggestion })}
                      size='compact'
                    >
                      {active ? 'Reemplazar' : 'Vincular'}
                    </Button>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>

        {conversation.opportunity_links.length > 0 ? (
          <p className='mt-4 border-t border-slate-200 pt-3 text-[0.6875rem] leading-5 text-slate-500'>
            El historial conserva {conversation.opportunity_links.length}{' '}
            {conversation.opportunity_links.length === 1 ? 'vínculo' : 'vínculos'}.
          </p>
        ) : null}
      </div>

      <Modal
        closeDisabled={isLinking}
        description='El historial de asociaciones se conserva y ninguna oportunidad se elimina.'
        isOpen={Boolean(confirmation)}
        onClose={() => setConfirmation(null)}
        title={confirmationTitle}
      >
        <div className='px-5 py-5'>
          <p className='text-sm leading-6 text-slate-700'>
            {confirmation?.kind === 'unlink'
              ? `La oportunidad #${confirmation.opportunity.id} dejará de ser la asociación activa.`
              : `La oportunidad #${confirmation?.opportunity.id ?? ''} quedará como asociación activa de esta conversación.`}
          </p>
          <div className='mt-5 flex justify-end gap-2'>
            <Button
              data-modal-initial-focus={confirmation?.kind === 'unlink' ? true : undefined}
              disabled={isLinking}
              onClick={() => setConfirmation(null)}
              size='compact'
            >
              Cancelar
            </Button>
            <Button
              data-modal-initial-focus={confirmation?.kind === 'link' ? true : undefined}
              disabled={isLinking}
              onClick={() => void confirm()}
              size='compact'
              variant={confirmation?.kind === 'unlink' ? 'danger' : 'primary'}
            >
              {isLinking ? 'Guardando…' : 'Confirmar'}
            </Button>
          </div>
        </div>
      </Modal>
    </aside>
  )
}
