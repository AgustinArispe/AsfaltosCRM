import { useEffect, useState } from 'react'
import { navigateRoute } from '../routing/router'
import { ConfirmationDialog } from '../shared/ConfirmationDialog'
import { Drawer } from '../shared/Drawer'
import { Icon } from '../shared/Icon'
import { ChatPanel } from '../whatsapp/ChatPanel'
import { ConversationList } from '../whatsapp/ConversationList'
import { CrmContextPanel } from '../whatsapp/CrmContextPanel'
import { HumanTemplateSelector } from '../whatsapp/HumanTemplateSelector'
import { useWhatsAppInbox } from '../whatsapp/useWhatsAppInbox'
import { CustomerDetailPage } from './CustomerDetailPage'
import { OpportunityDetailPage } from './OpportunityDetailPage'

export function WhatsAppInboxPage({ initialConversationId }: { initialConversationId?: number }) {
  const [isContextOpen, setIsContextOpen] = useState(false)
  const inbox = useWhatsAppInbox(
    initialConversationId,
    isContextOpen,
    new URLSearchParams(window.location.search).get('waiting') === 'true',
  )
  const [isTemplateOpen, setIsTemplateOpen] = useState(false)
  const [templateMode, setTemplateMode] = useState<'all' | 'recontact'>('all')
  const [isDeleteConfirmationOpen, setIsDeleteConfirmationOpen] = useState(false)
  const [openCustomerId, setOpenCustomerId] = useState<number | null>(null)
  const [openOpportunityId, setOpenOpportunityId] = useState<number | null>(null)
  const [isConversationSidebarCollapsed, setIsConversationSidebarCollapsed] = useState(false)

  useEffect(() => {
    void inbox.selectedConversationId
    setIsContextOpen(false)
    setIsTemplateOpen(false)
    setTemplateMode('all')
  }, [inbox.selectedConversationId])

  useEffect(() => {
    if (initialConversationId && !inbox.selectedConversationId && inbox.detailStatus === 'idle') {
      navigateRoute({ kind: 'workspace', workspace: 'whatsapp' }, { replace: true })
    }
  }, [inbox.detailStatus, inbox.selectedConversationId, initialConversationId])

  const returnToConversationList = () => {
    const conversationId = inbox.selectedConversationId
    inbox.selectConversation(null)
    navigateRoute({ kind: 'workspace', workspace: 'whatsapp' }, { replace: true })
    if (!conversationId) return
    window.requestAnimationFrame(() => {
      document
        .getElementById(`whatsapp-conversation-${conversationId}`)
        ?.focus({ preventScroll: true })
    })
  }

  const setConversationSidebarCollapsed = (collapsed: boolean) => {
    setIsConversationSidebarCollapsed(collapsed)
    window.requestAnimationFrame(() => {
      document
        .getElementById(
          collapsed ? 'whatsapp-conversations-expand' : 'whatsapp-conversations-collapse',
        )
        ?.focus({ preventScroll: true })
    })
  }

  return (
    <div className='whatsapp-workspace relative h-[calc(100dvh-4.75rem)] min-h-[36rem] overflow-hidden rounded-[var(--radius-surface)] bg-[var(--surface-primary)] lg:h-[calc(100dvh-2rem)]'>
      <div
        className={[
          'grid h-full min-h-0 min-w-0',
          isConversationSidebarCollapsed
            ? 'md:grid-cols-[3.5rem_minmax(0,1fr)]'
            : 'md:grid-cols-[19rem_minmax(0,1fr)] xl:grid-cols-[20rem_minmax(0,1fr)]',
        ].join(' ')}
      >
        <div
          className={[
            'min-h-0',
            isConversationSidebarCollapsed
              ? inbox.selectedConversationId
                ? 'hidden'
                : 'block md:hidden'
              : inbox.selectedConversationId
                ? 'hidden md:block'
                : 'block',
          ].join(' ')}
        >
          <ConversationList
            conversations={inbox.conversations}
            error={inbox.conversationError}
            hasMore={Boolean(inbox.nextConversationCursor)}
            onLoadMore={() => void inbox.loadMoreConversations()}
            onCollapse={() => setConversationSidebarCollapsed(true)}
            onRetry={inbox.retryConversationLoad}
            onSearchChange={inbox.setSearchDraft}
            onSelect={(conversationId) => {
              setIsContextOpen(false)
              inbox.selectConversation(conversationId)
              navigateRoute(
                { kind: 'conversation', conversationId },
                { origin: { kind: 'workspace', workspace: 'whatsapp' } },
              )
            }}
            onUnreadChange={inbox.setUnreadOnly}
            onWaitingChange={inbox.setWaitingOnly}
            search={inbox.searchDraft}
            selectedConversationId={inbox.selectedConversationId}
            status={inbox.conversationStatus}
            unreadOnly={inbox.unreadOnly}
            waitingOnly={inbox.waitingOnly}
          />
        </div>

        {isConversationSidebarCollapsed ? (
          <aside
            aria-label='Conversaciones contraídas'
            className='hidden h-full min-h-0 flex-col items-center gap-2 border-e border-[var(--divider)] bg-[var(--surface-secondary)] px-1.5 py-3 md:flex'
          >
            <button
              aria-controls='whatsapp-conversations-panel'
              aria-expanded={false}
              aria-label='Mostrar conversaciones'
              className='ui-pressable grid size-11 place-items-center rounded-[var(--radius-control)] text-[var(--text-secondary)] outline-none hover:bg-[var(--surface-interactive)] focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]'
              id='whatsapp-conversations-expand'
              onClick={() => setConversationSidebarCollapsed(false)}
              title='Mostrar conversaciones'
              type='button'
            >
              <Icon className='size-5' name='inbox' />
            </button>
            <span className='text-xs tabular-nums text-[var(--text-tertiary)]'>
              {inbox.conversations.length}
            </span>
          </aside>
        ) : null}

        <div
          className={[
            'min-h-0 min-w-0',
            inbox.selectedConversationId ? 'flex' : 'hidden md:flex',
          ].join(' ')}
        >
          <ChatPanel
            conversation={inbox.selectedDetail}
            detailError={inbox.detailError}
            detailStatus={inbox.detailStatus}
            hasFailedSend={Boolean(inbox.failedSend)}
            hasOlderMessages={Boolean(inbox.nextMessageCursor)}
            isLoadingOlder={inbox.isLoadingOlder}
            isContextOpen={isContextOpen}
            isOnline={inbox.isOnline}
            isSending={inbox.isSending}
            isMarkingHandled={inbox.isMarkingHandled}
            handleError={inbox.handleError}
            messageError={inbox.messageError}
            messageStatus={inbox.messageStatus}
            messages={inbox.messages}
            onBack={returnToConversationList}
            onDiscardFailed={inbox.discardFailedSend}
            onDelete={() => setIsDeleteConfirmationOpen(true)}
            onMarkHandled={() => void inbox.markConversationHandled()}
            onLoadOlder={inbox.loadOlderMessages}
            onOpenContext={() => setIsContextOpen(true)}
            onOpenTemplates={() => {
              setTemplateMode('all')
              setIsTemplateOpen(true)
            }}
            onOpenRecontactTemplates={() => {
              setTemplateMode('recontact')
              setIsTemplateOpen(true)
            }}
            onResend={inbox.resendMessage}
            onRetryFailed={inbox.retryFailedSend}
            onRetryLoad={inbox.retrySelectedLoad}
            onSend={inbox.sendNewMessage}
            sendError={inbox.sendError}
          />
        </div>
      </div>

      <Drawer isOpen={isContextOpen} onClose={() => setIsContextOpen(false)} title='Contexto CRM'>
        <div id='whatsapp-context-drawer'>
          {isContextOpen && inbox.selectedDetail ? (
            <CrmContextPanel
              key={`drawer-${inbox.selectedDetail.id}`}
              conversation={inbox.selectedDetail}
              customerDetail={inbox.customerDetail}
              error={inbox.contextError}
              isCreatingOpportunity={inbox.isCreatingOpportunity}
              isLinking={inbox.isLinking}
              linkError={inbox.linkError}
              onRetryContext={inbox.retryContextLoad}
              onCreateOpportunity={inbox.createOpportunity}
              onOpenCustomer={setOpenCustomerId}
              onOpenOpportunity={setOpenOpportunityId}
              onUpdateLink={inbox.updateOpportunityLink}
              opportunityDetail={inbox.opportunityDetail}
              status={inbox.contextStatus}
            />
          ) : null}
        </div>
      </Drawer>
      {openCustomerId ? (
        <CustomerDetailPage customerId={openCustomerId} onClose={() => setOpenCustomerId(null)} />
      ) : null}
      {openOpportunityId ? (
        <OpportunityDetailPage
          onClose={() => setOpenOpportunityId(null)}
          opportunityId={openOpportunityId}
        />
      ) : null}
      <HumanTemplateSelector
        error={inbox.humanTemplateError}
        isOpen={isTemplateOpen}
        isSending={inbox.isSending}
        mode={templateMode}
        onClose={() => setIsTemplateOpen(false)}
        onReload={inbox.loadHumanTemplates}
        onSend={inbox.sendHumanTemplate}
        status={inbox.humanTemplateStatus}
        templates={inbox.humanTemplates}
      />
      <ConfirmationDialog
        confirmLabel='Eliminar conversación'
        description='La conversación dejará de mostrarse en la bandeja. Sus mensajes y vínculos comerciales se conservarán.'
        error={inbox.detailError}
        isOpen={isDeleteConfirmationOpen}
        isPending={inbox.isHidingConversation}
        onCancel={() => setIsDeleteConfirmationOpen(false)}
        onConfirm={() => {
          void inbox.hideConversation().then((hidden) => {
            if (hidden) setIsDeleteConfirmationOpen(false)
          })
        }}
        pendingLabel='Eliminando conversación…'
        title='¿Eliminar conversación?'
        variant='danger'
      >
        <p className='text-sm leading-6 text-[var(--text-secondary)]'>
          Podrá volver a aparecer si el cliente escribe nuevamente por WhatsApp.
        </p>
      </ConfirmationDialog>
    </div>
  )
}
