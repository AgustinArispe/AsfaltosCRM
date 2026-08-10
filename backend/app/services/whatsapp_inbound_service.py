from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Customer,
    LeadSource,
    Opportunity,
    WhatsAppAttachment,
    WhatsAppConversation,
    WhatsAppConversationOpportunity,
    WhatsAppConversationResolution,
    WhatsAppDirection,
    WhatsAppMessage,
    WhatsAppMessageType,
    WhatsAppOpportunityLinkSource,
    WhatsAppProviderState,
    WhatsAppStorageStatus,
)
from app.services.customer_identity_service import (
    CustomerIdentityResolver,
    acquire_advisory_locks,
    comparable_phone,
    customer_identity_locks,
    normalize_optional_text,
)
from app.services.errors import (
    InvalidWhatsAppMessageError,
    WhatsAppIdempotencyConflictError,
)
from app.services.opportunity_service import OpportunityService
from app.services.whatsapp_conversation_service import (
    OPEN_OPPORTUNITY_STATUSES,
    WhatsAppConversationService,
)
from app.services.whatsapp_projection_service import (
    later_datetime,
    recompute_response_projection,
)
from app.whatsapp import WhatsAppProvider, WindowEvaluationContext


@dataclass(frozen=True, slots=True)
class InboundAttachmentInput:
    provider_media_id: str
    mime_type: str | None
    filename: str | None
    size_bytes: int | None


@dataclass(frozen=True, slots=True)
class InboundMessageInput:
    external_message_id: str
    external_phone: str
    provider_contact_id: str | None
    display_name: str | None
    message_type: WhatsAppMessageType
    body: str | None
    provider_message_at: datetime
    attachment: InboundAttachmentInput | None = None


@dataclass(frozen=True, slots=True)
class InboundMessageResult:
    conversation_id: int
    message_id: int
    customer_id: int | None
    opportunity_id: int | None
    suggested_opportunity_ids: tuple[int, ...]
    created: bool


@dataclass(frozen=True, slots=True)
class _NormalizedInbound:
    external_message_id: str
    external_phone: str
    phone_match_key: str
    provider_contact_id: str | None
    display_name: str | None
    message_type: WhatsAppMessageType
    body: str | None
    provider_message_at: datetime
    attachment: InboundAttachmentInput | None


class WhatsAppInboundService:
    def __init__(self, session: Session, provider: WhatsAppProvider) -> None:
        self._session = session
        self._provider = provider

    def receive(
        self,
        message_input: InboundMessageInput,
        *,
        now: datetime | None = None,
    ) -> InboundMessageResult:
        received_at = self._aware_utc(now or datetime.now(UTC))
        normalized = self._normalize(message_input)
        window = self._provider.evaluate_window(
            WindowEvaluationContext(
                last_inbound_at=normalized.provider_message_at,
                now=received_at,
            )
        )
        with self._session.begin():
            acquire_advisory_locks(
                self._session,
                (
                    ("whatsapp-message", normalized.external_message_id),
                    *customer_identity_locks(None, normalized.phone_match_key),
                ),
            )
            existing = self._session.scalar(
                select(WhatsAppMessage).where(
                    WhatsAppMessage.external_message_id
                    == normalized.external_message_id
                )
            )
            if existing is not None:
                return self._replay_result(existing, normalized)

            conversation = self._session.scalar(
                select(WhatsAppConversation)
                .where(
                    WhatsAppConversation.phone_match_key == normalized.phone_match_key
                )
                .with_for_update()
            )
            opportunity: Opportunity | None = None
            if conversation is None:
                conversation, opportunity = self._create_conversation(
                    normalized,
                    created_at=received_at,
                )
            else:
                self._refresh_existing_conversation(conversation, normalized)

            message = WhatsAppMessage(
                conversation_id=conversation.id,
                external_message_id=normalized.external_message_id,
                client_generated_id=None,
                direction=WhatsAppDirection.INBOUND,
                message_type=normalized.message_type,
                body=normalized.body,
                sent_by_user_id=None,
                dispatch_state=None,
                provider_state=WhatsAppProviderState.RECEIVED,
                provider_message_at=normalized.provider_message_at,
            )
            self._session.add(message)
            self._session.flush()
            if normalized.attachment is not None:
                self._session.add(
                    WhatsAppAttachment(
                        message_id=message.id,
                        provider_media_id=(normalized.attachment.provider_media_id),
                        media_type=normalized.message_type,
                        mime_type=normalized.attachment.mime_type,
                        filename=normalized.attachment.filename,
                        size_bytes=normalized.attachment.size_bytes,
                        storage_status=WhatsAppStorageStatus.PENDING,
                    )
                )

            conversation.last_message_at = later_datetime(
                conversation.last_message_at,
                normalized.provider_message_at,
            )
            conversation.last_inbound_at = later_datetime(
                conversation.last_inbound_at,
                normalized.provider_message_at,
            )
            conversation.unread_count += 1
            conversation.window_expires_at = later_datetime(
                conversation.window_expires_at,
                window.window_expires_at,
            )
            recompute_response_projection(
                self._session,
                conversation,
                now=received_at,
            )
            self._session.flush()

            suggestions = (
                []
                if opportunity is not None
                else self._suggestions_for_customer(conversation.customer_id)
            )
            return InboundMessageResult(
                conversation_id=conversation.id,
                message_id=message.id,
                customer_id=conversation.customer_id,
                opportunity_id=opportunity.id if opportunity is not None else None,
                suggested_opportunity_ids=tuple(item.id for item in suggestions),
                created=True,
            )

    def _create_conversation(
        self,
        inbound: _NormalizedInbound,
        *,
        created_at: datetime,
    ) -> tuple[WhatsAppConversation, Opportunity | None]:
        resolution = CustomerIdentityResolver(self._session).resolve(
            normalized_email=None,
            phone_match_key=inbound.phone_match_key,
            lock_rows=True,
        )
        customer: Customer | None = None
        opportunity: Opportunity | None = None
        needs_review = resolution.is_ambiguous or resolution.has_deleted_matches
        if not needs_review:
            customer = resolution.customer
        if customer is None and not needs_review:
            customer = Customer(
                name=self._customer_name(inbound),
                phone=inbound.external_phone,
                legendary_historical_override=False,
            )
            self._session.add(customer)
            self._session.flush()
            opportunity = OpportunityService(
                self._session
            ).create_opportunity_in_transaction(
                customer_id=customer.id,
                source=LeadSource.WHATSAPP,
                assigned_user_id=None,
                changed_by_user_id=None,
            )

        conversation = WhatsAppConversation(
            customer_id=customer.id if customer is not None else None,
            external_phone=inbound.external_phone,
            phone_match_key=inbound.phone_match_key,
            provider_contact_id=inbound.provider_contact_id,
            display_name=inbound.display_name,
            resolution_status=(
                WhatsAppConversationResolution.NEEDS_REVIEW
                if needs_review
                else WhatsAppConversationResolution.RESOLVED
            ),
        )
        self._session.add(conversation)
        self._session.flush()
        if opportunity is not None:
            WhatsAppConversationService(self._session).link_opportunity_in_transaction(
                conversation=conversation,
                opportunity_id=opportunity.id,
                link_source=WhatsAppOpportunityLinkSource.AUTO_NEW_CONTACT,
                linked_by_user_id=None,
                linked_at=created_at,
            )
        return conversation, opportunity

    def _refresh_existing_conversation(
        self,
        conversation: WhatsAppConversation,
        inbound: _NormalizedInbound,
    ) -> None:
        if conversation.display_name is None and inbound.display_name is not None:
            conversation.display_name = inbound.display_name
        if (
            conversation.provider_contact_id is None
            and inbound.provider_contact_id is not None
        ):
            conversation.provider_contact_id = inbound.provider_contact_id
        if conversation.customer_id is not None:
            customer = self._session.get(Customer, conversation.customer_id)
            if customer is not None and customer.deleted_at is not None:
                conversation.resolution_status = (
                    WhatsAppConversationResolution.NEEDS_REVIEW
                )

    def _replay_result(
        self,
        message: WhatsAppMessage,
        inbound: _NormalizedInbound,
    ) -> InboundMessageResult:
        conversation = self._session.get(
            WhatsAppConversation,
            message.conversation_id,
        )
        if conversation is None:
            raise RuntimeError("Persisted WhatsApp message has no conversation")
        attachment = message.attachment
        same_attachment = (
            inbound.attachment is None
            if attachment is None
            else inbound.attachment is not None
            and attachment.provider_media_id == inbound.attachment.provider_media_id
            and attachment.mime_type == inbound.attachment.mime_type
            and attachment.filename == inbound.attachment.filename
            and attachment.size_bytes == inbound.attachment.size_bytes
        )
        if not (
            conversation.phone_match_key == inbound.phone_match_key
            and message.message_type is inbound.message_type
            and message.body == inbound.body
            and message.provider_message_at == inbound.provider_message_at
            and same_attachment
        ):
            raise WhatsAppIdempotencyConflictError(
                "External WhatsApp message ID was reused with different data"
            )
        linked_opportunity_id = self._session.scalar(
            select(WhatsAppConversationOpportunity.opportunity_id).where(
                WhatsAppConversationOpportunity.conversation_id == conversation.id,
                WhatsAppConversationOpportunity.unlinked_at.is_(None),
            )
        )
        return InboundMessageResult(
            conversation_id=conversation.id,
            message_id=message.id,
            customer_id=conversation.customer_id,
            opportunity_id=linked_opportunity_id,
            suggested_opportunity_ids=tuple(
                item.id
                for item in self._suggestions_for_customer(conversation.customer_id)
            ),
            created=False,
        )

    def _suggestions_for_customer(
        self,
        customer_id: int | None,
    ) -> list[Opportunity]:
        if customer_id is None:
            return []
        return list(
            self._session.scalars(
                select(Opportunity)
                .where(
                    Opportunity.customer_id == customer_id,
                    Opportunity.status.in_(OPEN_OPPORTUNITY_STATUSES),
                    Opportunity.deleted_at.is_(None),
                )
                .order_by(Opportunity.created_at.desc(), Opportunity.id.desc())
            )
        )

    @staticmethod
    def _normalize(message_input: InboundMessageInput) -> _NormalizedInbound:
        external_id = message_input.external_message_id.strip()
        external_phone = message_input.external_phone.strip()
        phone_match_key = comparable_phone(external_phone)
        display_name = normalize_optional_text(message_input.display_name)
        provider_contact_id = normalize_optional_text(message_input.provider_contact_id)
        body = normalize_optional_text(message_input.body)
        provider_message_at = WhatsAppInboundService._aware_utc(
            message_input.provider_message_at
        )
        if not external_id:
            raise InvalidWhatsAppMessageError("External message ID is required")
        if phone_match_key is None:
            raise InvalidWhatsAppMessageError("A matchable phone number is required")
        if message_input.message_type is WhatsAppMessageType.TEXT and body is None:
            raise InvalidWhatsAppMessageError("Text inbound requires a body")
        if message_input.message_type is WhatsAppMessageType.TEXT:
            if message_input.attachment is not None:
                raise InvalidWhatsAppMessageError(
                    "Text inbound cannot include an attachment"
                )
        elif message_input.attachment is None:
            raise InvalidWhatsAppMessageError(
                "Media inbound requires attachment metadata"
            )
        return _NormalizedInbound(
            external_message_id=external_id,
            external_phone=external_phone,
            phone_match_key=phone_match_key,
            provider_contact_id=provider_contact_id,
            display_name=display_name,
            message_type=message_input.message_type,
            body=body,
            provider_message_at=provider_message_at,
            attachment=message_input.attachment,
        )

    @staticmethod
    def _customer_name(inbound: _NormalizedInbound) -> str:
        if inbound.display_name is not None:
            return inbound.display_name
        digits = "".join(
            character for character in inbound.phone_match_key if character.isdigit()
        )
        return f"Contacto WhatsApp ••••{digits[-4:]}"

    @staticmethod
    def _aware_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Datetime must be timezone-aware")
        return value.astimezone(UTC)
