import { useEffect, useState } from 'react'
import { navigateRoute } from '../routing/router'
import { Button } from '../shared/Button'
import { Drawer } from '../shared/Drawer'
import { ChatPanel } from '../whatsapp/ChatPanel'
import { ConversationList } from '../whatsapp/ConversationList'
import { CrmContextPanel } from '../whatsapp/CrmContextPanel'
import { HumanTemplateSelector } from '../whatsapp/HumanTemplateSelector'
import { useWhatsAppInbox } from '../whatsapp/useWhatsAppInbox'

export function WhatsAppInboxPage({ initialConversationId }: { initialConversationId?: number }) {
  const inbox = useWhatsAppInbox(initialConversationId)
  const [isContextOpen, setIsContextOpen] = useState(false)
  const [isContextCollapsed, setIsContextCollapsed] = useState(
    () => window.localStorage.getItem('faa.crm.whatsapp.context-collapsed') === 'true',
  )
  const [isTemplateOpen, setIsTemplateOpen] = useState(false)

  useEffect(() => {
    window.localStorage.setItem('faa.crm.whatsapp.context-collapsed', String(isContextCollapsed))
  }, [isContextCollapsed])

  useEffect(() => {
    void inbox.selectedConversationId
    setIsContextOpen(false)
    setIsTemplateOpen(false)
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

  const context = inbox.selectedDetail ? (
    <CrmContextPanel
      key={inbox.selectedDetail.id}
      conversation={inbox.selectedDetail}
      customerDetail={inbox.customerDetail}
      error={inbox.contextError}
      isCreatingOpportunity={inbox.isCreatingOpportunity}
      headingId='whatsapp-context-title'
      isLinking={inbox.isLinking}
      linkError={inbox.linkError}
      onRetryContext={inbox.retryContextLoad}
      onCreateOpportunity={inbox.createOpportunity}
      onUpdateLink={inbox.updateOpportunityLink}
      onCollapse={() => setIsContextCollapsed(true)}
      opportunityDetail={inbox.opportunityDetail}
      status={inbox.contextStatus}
    />
  ) : null

  return (
    <div className='whatsapp-workspace relative min-h-[36rem] overflow-hidden rounded-[var(--radius-surface)] bg-[var(--surface-primary)] lg:h-[calc(100dvh-7.75rem)]'>
      <div
        className={[
          'grid h-full min-h-0 md:grid-cols-[19rem_minmax(0,1fr)]',
          isContextCollapsed
            ? '2xl:grid-cols-[20rem_minmax(28rem,1fr)]'
            : '2xl:grid-cols-[20rem_minmax(28rem,1fr)_19rem]',
        ].join(' ')}
      >
        <div
          className={['min-h-0', inbox.selectedConversationId ? 'hidden md:block' : 'block'].join(
            ' ',
          )}
        >
          <ConversationList
            conversations={inbox.conversations}
            error={inbox.conversationError}
            hasMore={Boolean(inbox.nextConversationCursor)}
            onLoadMore={() => void inbox.loadMoreConversations()}
            onRetry={inbox.retryConversationLoad}
            onSearchChange={inbox.setSearchDraft}
            onSelect={(conversationId) => {
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

        <div
          className={['min-h-0', inbox.selectedConversationId ? 'flex' : 'hidden md:flex'].join(
            ' ',
          )}
        >
          <ChatPanel
            conversation={inbox.selectedDetail}
            detailError={inbox.detailError}
            detailStatus={inbox.detailStatus}
            hasFailedSend={Boolean(inbox.failedSend)}
            hasOlderMessages={Boolean(inbox.nextMessageCursor)}
            isLoadingOlder={inbox.isLoadingOlder}
            isContextOpen={isContextOpen}
            isContextCollapsed={isContextCollapsed}
            isOnline={inbox.isOnline}
            isSending={inbox.isSending}
            messageError={inbox.messageError}
            messageStatus={inbox.messageStatus}
            messages={inbox.messages}
            onBack={returnToConversationList}
            onDiscardFailed={inbox.discardFailedSend}
            onLoadOlder={inbox.loadOlderMessages}
            onOpenContext={() => {
              if (window.matchMedia?.('(min-width: 1536px)').matches && isContextCollapsed) {
                setIsContextCollapsed(false)
              } else {
                setIsContextOpen(true)
              }
            }}
            onOpenTemplates={() => setIsTemplateOpen(true)}
            onResend={inbox.resendMessage}
            onRetryFailed={inbox.retryFailedSend}
            onRetryLoad={inbox.retrySelectedLoad}
            onSend={inbox.sendNewMessage}
            sendError={inbox.sendError}
          />
        </div>

        <div
          className={
            isContextCollapsed
              ? 'hidden'
              : 'hidden min-h-0 border-s border-[var(--divider)] bg-[var(--surface-secondary)] 2xl:flex'
          }
        >
          {context}
        </div>
      </div>

      <Drawer
        description='Cliente y oportunidad asociados a la conversación'
        isOpen={isContextOpen}
        onClose={() => setIsContextOpen(false)}
        title='Contexto CRM'
      >
        <div id='whatsapp-context-drawer'>
          {isContextOpen && inbox.selectedDetail ? (
            <CrmContextPanel
              key={`drawer-${inbox.selectedDetail.id}`}
              conversation={inbox.selectedDetail}
              customerDetail={inbox.customerDetail}
              error={inbox.contextError}
              isCreatingOpportunity={inbox.isCreatingOpportunity}
              headingId='whatsapp-context-drawer-title'
              isLinking={inbox.isLinking}
              linkError={inbox.linkError}
              onRetryContext={inbox.retryContextLoad}
              onCreateOpportunity={inbox.createOpportunity}
              onUpdateLink={inbox.updateOpportunityLink}
              opportunityDetail={inbox.opportunityDetail}
              status={inbox.contextStatus}
            />
          ) : null}
        </div>
      </Drawer>
      {isContextCollapsed ? (
        <Button
          className='absolute right-3 top-3 hidden 2xl:inline-flex'
          onClick={() => setIsContextCollapsed(false)}
          size='compact'
          type='button'
          variant='ghost'
        >
          Mostrar contexto CRM
        </Button>
      ) : null}
      <HumanTemplateSelector
        error={inbox.humanTemplateError}
        isOpen={isTemplateOpen}
        isSending={inbox.isSending}
        onClose={() => setIsTemplateOpen(false)}
        onReload={inbox.loadHumanTemplates}
        onSend={inbox.sendHumanTemplate}
        status={inbox.humanTemplateStatus}
        templates={inbox.humanTemplates}
      />
    </div>
  )
}
