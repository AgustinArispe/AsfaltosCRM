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
import { Modal } from '../shared/Modal'
import { LoadingState } from '../shared/StatusStates'
import type { WhatsAppConversationDetail, WhatsAppOpportunitySummary } from './types'

type LinkConfirmation =
  | { kind: 'link'; opportunity: WhatsAppOpportunitySummary }
  | { kind: 'unlink'; opportunity: WhatsAppOpportunitySummary }

function ContextField({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className='text-[0.6875rem] font-semibold text-[var(--text-tertiary)]'>{label}</dt>
      <dd className='mt-0.5 break-words text-sm text-[var(--text-primary)]'>
        {value || 'No informado'}
      </dd>
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
    <article className='rounded-[var(--radius-control)] bg-[var(--surface-interactive)] px-3 py-3'>
      <div className='flex flex-wrap items-start justify-between gap-2'>
        <div>
          <p className='text-xs font-semibold text-[var(--text-tertiary)]'>
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
        <div className='mt-3 border-t border-[var(--subtle-border)] pt-3'>
          <p className='text-xs font-semibold text-[var(--text-secondary)]'>Productos y volumen</p>
          {detail.products.length > 0 ? (
            <ul className='mt-1.5 space-y-1 text-xs text-[var(--text-secondary)]'>
              {detail.products.map((quoted) => (
                <li className='flex justify-between gap-3' key={quoted.product.id}>
                  <span>{quoted.product.name}</span>
                  <span className='shrink-0 font-semibold text-[var(--text-primary)]'>
                    {formatQuantityKg(quoted.quantity_kg)}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className='mt-1 text-xs text-[var(--text-tertiary)]'>Sin cotización registrada.</p>
          )}
        </div>
      ) : null}
      <AppLink
        className='mt-3 inline-flex min-h-11 items-center text-xs font-semibold text-[var(--text-secondary)] underline decoration-[var(--subtle-border)] underline-offset-4 outline-none hover:text-[var(--text-primary)] focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]'
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
  isCreatingOpportunity,
  linkError,
  headingId = 'whatsapp-context-title',
  onRetryContext,
  onUpdateLink,
  onCreateOpportunity,
  onCollapse,
}: {
  conversation: WhatsAppConversationDetail
  customerDetail: CustomerDetail | null
  opportunityDetail: OpportunityDetail | null
  status: 'idle' | 'loading' | 'ready' | 'error'
  error: string | null
  isLinking: boolean
  isCreatingOpportunity: boolean
  linkError: string | null
  headingId?: string
  onRetryContext: () => void
  onUpdateLink: (opportunityId: number | null) => Promise<void>
  onCreateOpportunity: () => Promise<void>
  onCollapse?: () => void
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
    <aside
      aria-labelledby={headingId}
      className='whatsapp-context flex min-h-0 flex-col bg-[var(--surface-secondary)]'
    >
      <header className='flex shrink-0 items-start justify-between gap-3 border-b border-[var(--subtle-border)] px-4 py-3'>
        <div>
          <h2 className='text-sm font-semibold text-[var(--text-primary)]' id={headingId}>
            Contexto CRM
          </h2>
          <p className='mt-0.5 text-xs text-[var(--text-tertiary)]'>
            Información para responder mejor
          </p>
        </div>
        {onCollapse ? (
          <Button onClick={onCollapse} size='compact' type='button' variant='ghost'>
            Ocultar contexto
          </Button>
        ) : null}
      </header>
      <div className='min-h-0 flex-1 overflow-y-auto px-4 py-4'>
        {conversation.resolution_status === 'NEEDS_REVIEW' ? (
          <div
            className='rounded-[var(--radius-control)] border border-[var(--destructive-border)] bg-[var(--destructive-subtle)] px-3 py-3'
            role='status'
          >
            <p className='text-sm font-semibold text-[var(--destructive-text)]'>
              Identidad pendiente
            </p>
            <p className='mt-1 text-xs leading-5 text-[var(--destructive-text)]'>
              El teléfono coincide de forma ambigua. No se puede responder ni vincular una
              oportunidad hasta resolverlo.
            </p>
          </div>
        ) : null}

        <section aria-labelledby='context-customer-title' className='mt-1'>
          <div className='flex items-center justify-between gap-3'>
            <h3
              className='text-sm font-semibold text-[var(--text-primary)]'
              id='context-customer-title'
            >
              Cliente
            </h3>
            {customer?.is_available ? (
              <AppLink
                className='inline-flex min-h-11 items-center text-xs font-semibold text-[var(--text-secondary)] underline decoration-[var(--subtle-border)] underline-offset-4 outline-none hover:text-[var(--text-primary)] focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]'
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
              <p className='text-xs font-medium text-[var(--destructive-text)]' role='status'>
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
          className='mt-5 border-t border-[var(--subtle-border)] pt-4'
        >
          <h3
            className='text-sm font-semibold text-[var(--text-primary)]'
            id='context-opportunity-title'
          >
            Oportunidad comercial
          </h3>
          {linkError ? (
            <p className='mt-2 text-xs font-medium text-[var(--destructive-text)]' role='alert'>
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
            <div className='mt-2'>
              <p className='text-xs leading-5 text-[var(--text-tertiary)]'>
                No hay una oportunidad activa vinculada. El CRM no crea una automáticamente.
              </p>
              {conversation.resolution_status === 'RESOLVED' && customer?.is_available ? (
                <Button
                  className='mt-2'
                  disabled={isCreatingOpportunity}
                  onClick={() => void onCreateOpportunity()}
                  size='compact'
                  type='button'
                  variant='ghost'
                >
                  {isCreatingOpportunity ? 'Creando…' : 'Crear oportunidad'}
                </Button>
              ) : null}
            </div>
          )}

          {conversation.opportunity_suggestions.length > 0 ? (
            <div className='mt-4'>
              <p className='text-xs font-semibold text-[var(--text-secondary)]'>
                {active ? 'Otras oportunidades abiertas' : 'Sugerencias abiertas'}
              </p>
              <ul className='mt-2 space-y-2'>
                {conversation.opportunity_suggestions.map((suggestion) => (
                  <li
                    className='flex items-center justify-between gap-2 rounded-[var(--radius-control)] border border-[var(--subtle-border)] px-3 py-2'
                    key={suggestion.id}
                  >
                    <span className='min-w-0'>
                      <span className='block text-xs font-semibold text-[var(--text-primary)]'>
                        Oportunidad #{suggestion.id}
                      </span>
                      <span className='text-[0.6875rem] text-[var(--text-tertiary)]'>
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
          <p className='mt-4 border-t border-[var(--subtle-border)] pt-3 text-[0.6875rem] leading-5 text-[var(--text-tertiary)]'>
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
          <p className='text-sm leading-6 text-[var(--text-secondary)]'>
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
