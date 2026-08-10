from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.schemas.whatsapp import (
    AttachmentResponse,
    ConversationDetailResponse,
    ConversationSummaryResponse,
    CustomerSummaryResponse,
    MessageResponse,
    MessageStatusResponse,
    OpportunityLinkResponse,
    OpportunitySummaryResponse,
    OutboundMessageResponse,
    UserSummaryResponse,
    WhatsAppWindowReason,
)
from app.services.whatsapp_query_projections import (
    AttachmentProjection,
    ConversationDetailProjection,
    ConversationSummaryProjection,
    CustomerSummaryProjection,
    MessageProjection,
    OpportunityLinkProjection,
    OpportunitySummaryProjection,
    UserSummaryProjection,
)
from app.whatsapp import WhatsAppProvider, WindowDecision, WindowEvaluationContext


class WhatsAppApiPresenter:
    def __init__(self, provider: WhatsAppProvider) -> None:
        self._provider = provider

    def conversation_summary(
        self,
        projection: ConversationSummaryProjection,
        *,
        now: datetime,
    ) -> ConversationSummaryResponse:
        window = self._provider.evaluate_window(
            WindowEvaluationContext(
                last_inbound_at=projection.last_inbound_at,
                now=now,
            )
        )
        presented_window = _window(window)
        return ConversationSummaryResponse(
            id=projection.id,
            external_phone=projection.external_phone,
            display_name=projection.display_name,
            resolution_status=projection.resolution_status,
            customer=_customer(projection.customer),
            active_opportunity=_opportunity(projection.active_opportunity),
            opportunity_suggestions=[
                _opportunity_required(item)
                for item in projection.opportunity_suggestions
            ],
            last_message_at=projection.last_message_at,
            last_inbound_at=projection.last_inbound_at,
            last_outbound_at=projection.last_outbound_at,
            unread_count=projection.unread_count,
            waiting_for_response=projection.waiting_for_response,
            waiting_since_at=projection.waiting_since_at,
            can_send_freeform=presented_window.can_send_freeform,
            window_expires_at=presented_window.window_expires_at,
            template_required=presented_window.template_required,
            reason=presented_window.reason,
            updated_at=projection.updated_at,
            resource_updated_at=projection.resource_updated_at,
        )

    def conversation_detail(
        self,
        projection: ConversationDetailProjection,
        *,
        now: datetime,
    ) -> ConversationDetailResponse:
        summary = self.conversation_summary(projection.summary, now=now)
        return ConversationDetailResponse(
            id=summary.id,
            external_phone=summary.external_phone,
            display_name=summary.display_name,
            resolution_status=summary.resolution_status,
            customer=summary.customer,
            active_opportunity=summary.active_opportunity,
            opportunity_suggestions=summary.opportunity_suggestions,
            last_message_at=summary.last_message_at,
            last_inbound_at=summary.last_inbound_at,
            last_outbound_at=summary.last_outbound_at,
            unread_count=summary.unread_count,
            waiting_for_response=summary.waiting_for_response,
            waiting_since_at=summary.waiting_since_at,
            can_send_freeform=summary.can_send_freeform,
            window_expires_at=summary.window_expires_at,
            template_required=summary.template_required,
            reason=summary.reason,
            updated_at=summary.updated_at,
            resource_updated_at=summary.resource_updated_at,
            opportunity_links=[
                _opportunity_link(link) for link in projection.opportunity_links
            ],
            created_at=projection.created_at,
        )

    def message(self, projection: MessageProjection) -> MessageResponse:
        return MessageResponse(
            id=projection.id,
            conversation_id=projection.conversation_id,
            external_message_id=projection.external_message_id,
            client_generated_id=projection.client_generated_id,
            direction=projection.direction,
            message_type=projection.message_type,
            body=projection.body,
            sent_by=_user(projection.sent_by),
            retry_of_message_id=projection.retry_of_message_id,
            is_retry=projection.is_retry,
            message_at=projection.message_at,
            attachment=_attachment(projection.attachment),
            status=MessageStatusResponse(
                dispatch_state=projection.status.dispatch_state,
                provider_state=projection.status.provider_state,
                accepted_at=projection.status.accepted_at,
                sent_at=projection.status.sent_at,
                delivered_at=projection.status.delivered_at,
                read_at=projection.status.read_at,
                failed_at=projection.status.failed_at,
                error_code=projection.status.error_code,
                error_message=projection.status.error_message,
            ),
            created_at=projection.created_at,
            updated_at=projection.updated_at,
            resource_updated_at=projection.resource_updated_at,
        )

    def outbound_message(
        self,
        projection: MessageProjection,
        conversation: ConversationSummaryProjection,
        *,
        now: datetime,
    ) -> OutboundMessageResponse:
        window = self._provider.evaluate_window(
            WindowEvaluationContext(
                last_inbound_at=conversation.last_inbound_at,
                now=now,
            )
        )
        presented_window = _window(window)
        return OutboundMessageResponse(
            message=self.message(projection),
            can_send_freeform=presented_window.can_send_freeform,
            window_expires_at=presented_window.window_expires_at,
            template_required=presented_window.template_required,
            reason=presented_window.reason,
        )


@dataclass(frozen=True, slots=True)
class _WindowPresentation:
    can_send_freeform: bool
    window_expires_at: datetime | None
    template_required: bool
    reason: WhatsAppWindowReason | None


def _window(decision: WindowDecision) -> _WindowPresentation:
    return _WindowPresentation(
        can_send_freeform=decision.can_send_freeform,
        window_expires_at=decision.window_expires_at,
        template_required=not decision.can_send_freeform,
        reason=(
            None
            if decision.can_send_freeform
            else WhatsAppWindowReason.APPROVED_TEMPLATE_REQUIRED
        ),
    )


def _customer(
    projection: CustomerSummaryProjection | None,
) -> CustomerSummaryResponse | None:
    if projection is None:
        return None
    return CustomerSummaryResponse(
        id=projection.id,
        name=projection.name,
        company=projection.company,
        phone=projection.phone,
        province=projection.province,
        is_available=projection.is_available,
    )


def _user(
    projection: UserSummaryProjection | None,
) -> UserSummaryResponse | None:
    if projection is None:
        return None
    return UserSummaryResponse(
        id=projection.id,
        full_name=projection.full_name,
        role=projection.role,
    )


def _opportunity(
    projection: OpportunitySummaryProjection | None,
) -> OpportunitySummaryResponse | None:
    if projection is None:
        return None
    return _opportunity_required(projection)


def _opportunity_required(
    projection: OpportunitySummaryProjection,
) -> OpportunitySummaryResponse:
    return OpportunitySummaryResponse(
        id=projection.id,
        status=projection.status,
        source=projection.source,
        created_at=projection.created_at,
        linked_at=projection.linked_at,
        is_open=projection.is_open,
        is_available=projection.is_available,
    )


def _opportunity_link(
    projection: OpportunityLinkProjection,
) -> OpportunityLinkResponse:
    return OpportunityLinkResponse(
        id=projection.id,
        opportunity=_opportunity_required(projection.opportunity),
        linked_at=projection.linked_at,
        unlinked_at=projection.unlinked_at,
        linked_by=_user(projection.linked_by),
        link_source=projection.link_source,
        is_active=projection.is_active,
        is_actionable=projection.is_actionable,
    )


def _attachment(
    projection: AttachmentProjection | None,
) -> AttachmentResponse | None:
    if projection is None:
        return None
    return AttachmentResponse(
        id=projection.id,
        media_type=projection.media_type,
        mime_type=projection.mime_type,
        filename=projection.filename,
        size_bytes=projection.size_bytes,
        is_available=projection.is_available,
        content_url=(
            f"/api/whatsapp/attachments/{projection.id}/content"
            if projection.is_available
            else None
        ),
    )
