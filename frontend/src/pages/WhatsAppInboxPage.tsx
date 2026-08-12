import { useEffect, useState } from 'react'
import { Drawer } from '../shared/Drawer'
import { ChatPanel } from '../whatsapp/ChatPanel'
import { ConversationList } from '../whatsapp/ConversationList'
import { CrmContextPanel } from '../whatsapp/CrmContextPanel'
import { useWhatsAppInbox } from '../whatsapp/useWhatsAppInbox'

export function WhatsAppInboxPage() {
  const inbox = useWhatsAppInbox()
  const [isContextOpen, setIsContextOpen] = useState(false)

  useEffect(() => {
    void inbox.selectedConversationId
    setIsContextOpen(false)
  }, [inbox.selectedConversationId])

  const returnToConversationList = () => {
    const conversationId = inbox.selectedConversationId
    inbox.selectConversation(null)
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
      headingId='whatsapp-context-title'
      isLinking={inbox.isLinking}
      linkError={inbox.linkError}
      onRetryContext={inbox.retryContextLoad}
      onUpdateLink={inbox.updateOpportunityLink}
      opportunityDetail={inbox.opportunityDetail}
      status={inbox.contextStatus}
    />
  ) : null

  return (
    <div className='ui-panel min-h-[36rem] overflow-hidden lg:h-[calc(100dvh-7.75rem)]'>
      <div className='grid h-full min-h-0 md:grid-cols-[19rem_minmax(0,1fr)] 2xl:grid-cols-[20rem_minmax(28rem,1fr)_19rem]'>
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
            onSelect={inbox.selectConversation}
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
            isOnline={inbox.isOnline}
            isSending={inbox.isSending}
            messageError={inbox.messageError}
            messageStatus={inbox.messageStatus}
            messages={inbox.messages}
            onBack={returnToConversationList}
            onDiscardFailed={inbox.discardFailedSend}
            onLoadOlder={inbox.loadOlderMessages}
            onOpenContext={() => setIsContextOpen(true)}
            onResend={inbox.resendMessage}
            onRetryFailed={inbox.retryFailedSend}
            onRetryLoad={inbox.retrySelectedLoad}
            onSend={inbox.sendNewMessage}
            sendError={inbox.sendError}
          />
        </div>

        <div className='hidden min-h-0 border-l border-slate-200 2xl:flex'>{context}</div>
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
              headingId='whatsapp-context-drawer-title'
              isLinking={inbox.isLinking}
              linkError={inbox.linkError}
              onRetryContext={inbox.retryContextLoad}
              onUpdateLink={inbox.updateOpportunityLink}
              opportunityDetail={inbox.opportunityDetail}
              status={inbox.contextStatus}
            />
          ) : null}
        </div>
      </Drawer>
    </div>
  )
}
