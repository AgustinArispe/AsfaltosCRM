from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Customer,
    User,
    WhatsAppAttachment,
    WhatsAppBroadcastAuditEvent,
    WhatsAppBroadcastAuditEventType,
    WhatsAppBroadcastRecipient,
    WhatsAppBroadcastRecipientStatus,
    WhatsAppBroadcastTemplateParameter,
    WhatsAppConsentDecision,
    WhatsAppConversation,
    WhatsAppConversationResolution,
    WhatsAppDirection,
    WhatsAppDispatchState,
    WhatsAppHumanTemplateParameter,
    WhatsAppMessage,
    WhatsAppMessageOrigin,
    WhatsAppMessageType,
    WhatsAppProviderState,
    WhatsAppStorageStatus,
)
from app.services.customer_identity_service import (
    acquire_advisory_locks,
    comparable_phone,
)
from app.services.errors import (
    EntityNotFoundError,
    InactiveUserError,
    InvalidWhatsAppMessageError,
    WhatsAppConversationResolutionError,
    WhatsAppFreeformWindowClosedError,
    WhatsAppIdempotencyConflictError,
    WhatsAppReplyInProgressError,
)
from app.services.whatsapp_broadcast_projection_service import (
    recompute_broadcast_recipient_projection,
)
from app.services.whatsapp_consent_service import (
    WhatsAppConsentService,
    consent_dispatch_lock,
)
from app.services.whatsapp_projection_service import (
    earlier_datetime,
    later_datetime,
    recompute_response_projection,
)
from app.services.whatsapp_status_service import WhatsAppStatusService
from app.whatsapp import (
    ProviderMediaReference,
    ProviderRecipient,
    ProviderSendResult,
    RecordedProviderRequest,
    SendDocumentRequest,
    SendImageRequest,
    SendTemplateRequest,
    SendTextRequest,
    TemplateParameter,
    WhatsAppProvider,
    WhatsAppProviderError,
    WindowEvaluationContext,
)


@dataclass(frozen=True, slots=True)
class OutboundAttachmentInput:
    provider_media_id: str | None
    storage_key: str | None
    mime_type: str
    filename: str | None
    size_bytes: int | None = None
    media_type: WhatsAppMessageType | None = None


@dataclass(frozen=True, slots=True)
class OutboundMessageInput:
    conversation_id: int
    client_generated_id: UUID
    sent_by_user_id: int
    message_type: WhatsAppMessageType
    body: str | None
    attachment: OutboundAttachmentInput | None = None
    retry_of_message_id: int | None = None
    origin: WhatsAppMessageOrigin = WhatsAppMessageOrigin.HUMAN
    broadcast_recipient_id: int | None = None
    template_name: str | None = None
    template_language: str | None = None
    template_parameters: tuple[TemplateParameter, ...] = ()


@dataclass(frozen=True, slots=True)
class OutboundMessageResult:
    message_id: int
    dispatch_state: WhatsAppDispatchState
    external_message_id: str | None
    created: bool


class WhatsAppMessageService:
    def __init__(self, session: Session, provider: WhatsAppProvider) -> None:
        self._session = session
        self._provider = provider

    def send(
        self,
        message_input: OutboundMessageInput,
        *,
        now: datetime | None = None,
    ) -> OutboundMessageResult:
        requested_at = self._aware_utc(now or datetime.now(UTC))
        normalized = self._normalize(message_input)
        message_id, created, should_dispatch = self._prepare(
            normalized,
            requested_at=requested_at,
        )
        if not should_dispatch:
            return self._result(message_id, created=created)

        provider_request = self._start_dispatch(message_id, started_at=requested_at)
        if provider_request is None:
            return self._result(message_id, created=created)

        try:
            provider_result = self._dispatch(provider_request)
        except WhatsAppProviderError as error:
            return self._reconcile_error(
                message_id,
                error,
                reconciled_at=requested_at,
                created=created,
            )
        return self._reconcile_success(
            message_id,
            provider_result,
            reconciled_at=requested_at,
            created=created,
        )

    def _start_dispatch(
        self,
        message_id: int,
        *,
        started_at: datetime,
    ) -> RecordedProviderRequest | None:
        with self._session.begin():
            discovered = self._session.get(WhatsAppMessage, message_id)
            if discovered is None:
                raise EntityNotFoundError("WhatsAppMessage", message_id)

            discovered_recipient: WhatsAppBroadcastRecipient | None = None
            if discovered.broadcast_recipient_id is not None:
                discovered_recipient = self._session.get(
                    WhatsAppBroadcastRecipient,
                    discovered.broadcast_recipient_id,
                )
                if discovered_recipient is None:
                    raise RuntimeError("Broadcast Message has no recipient")
                acquire_advisory_locks(
                    self._session,
                    (
                        consent_dispatch_lock(
                            discovered_recipient.customer_id,
                            discovered_recipient.normalized_phone,
                        ),
                    ),
                )
                customer = self._session.scalar(
                    select(Customer)
                    .where(Customer.id == discovered_recipient.customer_id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
                recipient = self._session.scalar(
                    select(WhatsAppBroadcastRecipient)
                    .where(WhatsAppBroadcastRecipient.id == discovered_recipient.id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
                if recipient is None:
                    raise RuntimeError("Broadcast Message has no recipient")
            else:
                customer = None
                recipient = None

            conversation = self._session.scalar(
                select(WhatsAppConversation)
                .where(WhatsAppConversation.id == discovered.conversation_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if conversation is None:
                raise RuntimeError("Persisted WhatsApp message has no conversation")
            messages = tuple(
                self._session.scalars(
                    select(WhatsAppMessage)
                    .where(
                        WhatsAppMessage.id == message_id
                        if recipient is None
                        else WhatsAppMessage.broadcast_recipient_id == recipient.id
                    )
                    .order_by(WhatsAppMessage.id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
            )
            if not messages:
                raise EntityNotFoundError("WhatsAppMessage", message_id)
            message = next(
                (item for item in messages if item.id == message_id),
                None,
            )
            if message is None:
                raise EntityNotFoundError("WhatsAppMessage", message_id)

            if recipient is not None:
                latest = messages[-1]
                eligible_at = datetime.now(UTC)
                consent = WhatsAppConsentService(self._session).current(
                    recipient.customer_id,
                    recipient.normalized_phone,
                    now=eligible_at,
                )
                if (
                    customer is None
                    or customer.deleted_at is not None
                    or comparable_phone(customer.phone) != recipient.normalized_phone
                    or conversation.id != recipient.conversation_id
                    or conversation.customer_id != recipient.customer_id
                    or recipient.status
                    is not WhatsAppBroadcastRecipientStatus.IN_PROGRESS
                    or latest.id != message.id
                    or consent is None
                    or consent.decision is not WhatsAppConsentDecision.OPT_IN
                ):
                    self._block_broadcast_recipient(
                        recipient,
                        message,
                        now=eligible_at,
                    )
                    return None

            if message.dispatch_state is not WhatsAppDispatchState.PENDING:
                return None
            message.dispatch_state = WhatsAppDispatchState.IN_PROGRESS
            message.updated_at = later_datetime(message.updated_at, started_at)
            if recipient is not None:
                recompute_broadcast_recipient_projection(
                    self._session,
                    recipient,
                    now=started_at,
                )
            provider_request = self._build_provider_request(message)
            self._session.flush()
            return provider_request

    def _block_broadcast_recipient(
        self,
        recipient: WhatsAppBroadcastRecipient,
        message: WhatsAppMessage,
        *,
        now: datetime,
    ) -> None:
        recipient.status = WhatsAppBroadcastRecipientStatus.BLOCKED
        recipient.reason_code = "CONSENT_OR_PHONE_CHANGED"
        recipient.safe_error_code = None
        recipient.safe_error_message = None
        recipient.claim_token = None
        recipient.claimed_at = None
        recipient.updated_at = later_datetime(recipient.updated_at, now)
        self._session.add(
            WhatsAppBroadcastAuditEvent(
                broadcast_id=recipient.broadcast_id,
                recipient_id=recipient.id,
                message_id=message.id,
                event_type=WhatsAppBroadcastAuditEventType.BLOCKED,
                reason_code="CONSENT_OR_PHONE_CHANGED",
                occurred_at=now,
            )
        )

    def can_send_freeform(
        self,
        conversation_id: int,
        *,
        now: datetime | None = None,
    ) -> bool:
        evaluated_at = self._aware_utc(now or datetime.now(UTC))
        conversation = self._session.get(WhatsAppConversation, conversation_id)
        if conversation is None:
            raise EntityNotFoundError("WhatsAppConversation", conversation_id)
        decision = self._provider.evaluate_window(
            WindowEvaluationContext(
                last_inbound_at=conversation.last_inbound_at,
                now=evaluated_at,
            )
        )
        return decision.can_send_freeform

    def _prepare(
        self,
        message_input: OutboundMessageInput,
        *,
        requested_at: datetime,
    ) -> tuple[int, bool, bool]:
        with self._session.begin():
            acquire_advisory_locks(
                self._session,
                (
                    (
                        "whatsapp-outbound-message",
                        str(message_input.client_generated_id),
                    ),
                ),
            )
            if message_input.broadcast_recipient_id is not None:
                broadcast_recipient = self._session.scalar(
                    select(WhatsAppBroadcastRecipient)
                    .where(
                        WhatsAppBroadcastRecipient.id
                        == message_input.broadcast_recipient_id
                    )
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
                if broadcast_recipient is None:
                    raise InvalidWhatsAppMessageError(
                        "Broadcast outbound recipient does not exist"
                    )
            conversation = self._session.scalar(
                select(WhatsAppConversation)
                .where(WhatsAppConversation.id == message_input.conversation_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if conversation is None:
                raise EntityNotFoundError(
                    "WhatsAppConversation",
                    message_input.conversation_id,
                )
            self._validate_conversation(conversation)
            self._validate_user(message_input.sent_by_user_id)
            if (
                message_input.origin is WhatsAppMessageOrigin.HUMAN
                and message_input.template_name is None
            ):
                decision = self._provider.evaluate_window(
                    WindowEvaluationContext(
                        last_inbound_at=conversation.last_inbound_at,
                        now=requested_at,
                    )
                )
                conversation.window_expires_at = decision.window_expires_at
                if not decision.can_send_freeform:
                    raise WhatsAppFreeformWindowClosedError(
                        "Freeform WhatsApp window is closed; an approved template is required"
                    )

            existing = self._session.scalar(
                select(WhatsAppMessage)
                .where(
                    WhatsAppMessage.client_generated_id
                    == message_input.client_generated_id
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if existing is not None:
                self._assert_same_payload(existing, message_input)
                return (
                    existing.id,
                    False,
                    existing.dispatch_state is WhatsAppDispatchState.PENDING,
                )

            self._validate_retry(message_input)
            if message_input.origin is WhatsAppMessageOrigin.HUMAN:
                active_reply = self._session.scalar(
                    select(WhatsAppMessage.id)
                    .where(
                        WhatsAppMessage.conversation_id == conversation.id,
                        WhatsAppMessage.direction == WhatsAppDirection.OUTBOUND,
                        WhatsAppMessage.origin == WhatsAppMessageOrigin.HUMAN,
                        WhatsAppMessage.id != (message_input.retry_of_message_id or 0),
                        WhatsAppMessage.dispatch_state.in_(
                            {
                                WhatsAppDispatchState.PENDING,
                                WhatsAppDispatchState.IN_PROGRESS,
                                WhatsAppDispatchState.UNKNOWN,
                            }
                        ),
                    )
                    .limit(1)
                )
                if active_reply is not None:
                    raise WhatsAppReplyInProgressError(
                        "A direct reply is pending or has unknown acceptance"
                    )

            message = WhatsAppMessage(
                conversation_id=conversation.id,
                external_message_id=None,
                client_generated_id=message_input.client_generated_id,
                direction=WhatsAppDirection.OUTBOUND,
                message_type=message_input.message_type,
                origin=message_input.origin,
                body=message_input.body,
                sent_by_user_id=message_input.sent_by_user_id,
                retry_of_message_id=message_input.retry_of_message_id,
                broadcast_recipient_id=message_input.broadcast_recipient_id,
                template_name=message_input.template_name,
                template_language=message_input.template_language,
                dispatch_state=WhatsAppDispatchState.PENDING,
                provider_state=None,
            )
            self._session.add(message)
            self._session.flush()
            if message_input.attachment is not None:
                attachment = message_input.attachment
                self._session.add(
                    WhatsAppAttachment(
                        message_id=message.id,
                        provider_media_id=attachment.provider_media_id,
                        media_type=attachment.media_type or message_input.message_type,
                        mime_type=attachment.mime_type,
                        filename=attachment.filename,
                        size_bytes=attachment.size_bytes,
                        storage_key=attachment.storage_key,
                        storage_status=(
                            WhatsAppStorageStatus.AVAILABLE
                            if attachment.storage_key is not None
                            else WhatsAppStorageStatus.PENDING
                        ),
                    )
                )
            if (
                message_input.origin is WhatsAppMessageOrigin.HUMAN
                and message_input.template_name is not None
            ):
                self._session.add_all(
                    WhatsAppHumanTemplateParameter(
                        message_id=message.id,
                        position=position,
                        name=parameter.name,
                        value=parameter.value,
                    )
                    for position, parameter in enumerate(
                        message_input.template_parameters
                    )
                )
            conversation.updated_at = later_datetime(
                conversation.updated_at,
                requested_at,
            )
            self._session.flush()
            return message.id, True, True

    def _build_provider_request(
        self,
        message: WhatsAppMessage,
    ) -> RecordedProviderRequest:
        conversation = self._session.get(
            WhatsAppConversation,
            message.conversation_id,
        )
        if conversation is None or message.client_generated_id is None:
            raise RuntimeError("Persisted outbound message is incomplete")
        if message.origin is WhatsAppMessageOrigin.BROADCAST:
            if message.template_name is None or message.template_language is None:
                raise RuntimeError("Persisted broadcast message has no template")
            broadcast_recipient = self._session.scalar(
                select(WhatsAppBroadcastRecipient).where(
                    WhatsAppBroadcastRecipient.id == message.broadcast_recipient_id
                )
            )
            if broadcast_recipient is None:
                raise RuntimeError("Persisted broadcast message has no recipient")
            recipient = ProviderRecipient(phone=broadcast_recipient.normalized_phone)
            parameters = tuple(
                TemplateParameter(name=item.name, value=item.value)
                for item in self._session.scalars(
                    select(WhatsAppBroadcastTemplateParameter)
                    .where(
                        WhatsAppBroadcastTemplateParameter.broadcast_id
                        == broadcast_recipient.broadcast_id
                    )
                    .order_by(WhatsAppBroadcastTemplateParameter.position)
                )
            )
            header_media: ProviderMediaReference | None = None
            if message.attachment is not None:
                header_attachment = message.attachment
                header_media = ProviderMediaReference(
                    provider_media_id=header_attachment.provider_media_id,
                    storage_key=header_attachment.storage_key,
                    mime_type=header_attachment.mime_type,
                    filename=header_attachment.filename,
                )
            return SendTemplateRequest(
                recipient=recipient,
                client_generated_id=message.client_generated_id,
                template_name=message.template_name,
                language=message.template_language,
                parameters=parameters,
                header_media=header_media,
            )
        if message.template_name is not None:
            if message.template_language is None:
                raise RuntimeError("Persisted human template has no language")
            header_media = None
            if message.attachment is not None:
                header_attachment = message.attachment
                header_media = ProviderMediaReference(
                    provider_media_id=header_attachment.provider_media_id,
                    storage_key=header_attachment.storage_key,
                    mime_type=header_attachment.mime_type,
                    filename=header_attachment.filename,
                )
            parameters = tuple(
                TemplateParameter(name=item.name, value=item.value)
                for item in self._session.scalars(
                    select(WhatsAppHumanTemplateParameter)
                    .where(WhatsAppHumanTemplateParameter.message_id == message.id)
                    .order_by(WhatsAppHumanTemplateParameter.position)
                )
            )
            return SendTemplateRequest(
                recipient=ProviderRecipient(phone=conversation.external_phone),
                client_generated_id=message.client_generated_id,
                template_name=message.template_name,
                language=message.template_language,
                parameters=parameters,
                header_media=header_media,
            )
        recipient = ProviderRecipient(phone=conversation.external_phone)
        if message.message_type is WhatsAppMessageType.TEXT:
            if message.body is None:
                raise RuntimeError("Persisted text message has no body")
            return SendTextRequest(
                recipient=recipient,
                client_generated_id=message.client_generated_id,
                text=message.body,
            )
        attachment = message.attachment
        if attachment is None or attachment.mime_type is None:
            raise RuntimeError("Persisted media message has no attachment")
        media = ProviderMediaReference(
            provider_media_id=attachment.provider_media_id,
            storage_key=attachment.storage_key,
            mime_type=attachment.mime_type,
            filename=attachment.filename,
        )
        if message.message_type is WhatsAppMessageType.IMAGE:
            return SendImageRequest(
                recipient=recipient,
                client_generated_id=message.client_generated_id,
                media=media,
                caption=message.body,
            )
        return SendDocumentRequest(
            recipient=recipient,
            client_generated_id=message.client_generated_id,
            media=media,
            caption=message.body,
        )

    def _dispatch(self, request: RecordedProviderRequest) -> ProviderSendResult:
        if isinstance(request, SendTextRequest):
            return self._provider.send_text(request)
        if isinstance(request, SendImageRequest):
            return self._provider.send_image(request)
        if isinstance(request, SendDocumentRequest):
            return self._provider.send_document(request)
        return self._provider.send_template(request)

    def _reconcile_success(
        self,
        message_id: int,
        result: ProviderSendResult,
        *,
        reconciled_at: datetime,
        created: bool,
    ) -> OutboundMessageResult:
        accepted_at = self._aware_utc(result.accepted_at)
        external_id = result.external_message_id.strip()
        if not external_id:
            raise RuntimeError("Provider accepted a message without an external ID")
        with self._session.begin():
            acquire_advisory_locks(
                self._session,
                (("whatsapp-provider-message", external_id),),
            )
            message, conversation, recipient = self._message_graph_for_update(
                message_id
            )
            if message.dispatch_state is not WhatsAppDispatchState.IN_PROGRESS:
                return self._as_result(message, created=created)
            message.dispatch_state = WhatsAppDispatchState.ACCEPTED
            message.external_message_id = external_id
            message.accepted_at = accepted_at
            message.provider_state = result.initial_state
            message.provider_status_at = (
                accepted_at if result.initial_state is not None else None
            )
            if result.initial_state is WhatsAppProviderState.SENT:
                message.sent_at = accepted_at
            message.provider_error_code = None
            message.provider_error_message = None
            message.updated_at = later_datetime(message.updated_at, reconciled_at)
            conversation.last_message_at = later_datetime(
                conversation.last_message_at,
                accepted_at,
            )
            WhatsAppStatusService(self._session).attach_pending_events_in_transaction(
                message,
                now=reconciled_at,
            )
            recompute_response_projection(
                self._session,
                conversation,
                now=reconciled_at,
            )
            self._recompute_broadcast_recipient(
                recipient,
                now=reconciled_at,
            )
            self._session.flush()
            return self._as_result(message, created=created)

    def _reconcile_error(
        self,
        message_id: int,
        error: WhatsAppProviderError,
        *,
        reconciled_at: datetime,
        created: bool,
    ) -> OutboundMessageResult:
        with self._session.begin():
            message, _conversation, recipient = self._message_graph_for_update(
                message_id
            )
            if message.dispatch_state is WhatsAppDispatchState.IN_PROGRESS:
                message.dispatch_state = (
                    WhatsAppDispatchState.UNKNOWN
                    if error.details.acceptance_unknown
                    else WhatsAppDispatchState.DEFINITIVE_FAILED
                )
                message.provider_error_code = error.details.code
                message.provider_error_message = error.details.safe_message
                if not error.details.acceptance_unknown:
                    message.failed_at = earlier_datetime(
                        message.failed_at,
                        reconciled_at,
                    )
                message.updated_at = later_datetime(
                    message.updated_at,
                    reconciled_at,
                )
                self._recompute_broadcast_recipient(
                    recipient,
                    now=reconciled_at,
                )
                self._session.flush()
            return self._as_result(message, created=created)

    def _validate_retry(self, message_input: OutboundMessageInput) -> None:
        if message_input.retry_of_message_id is None:
            return
        original = self._session.scalar(
            select(WhatsAppMessage)
            .where(WhatsAppMessage.id == message_input.retry_of_message_id)
            .with_for_update()
        )
        if (
            original is None
            or original.direction is not WhatsAppDirection.OUTBOUND
            or original.conversation_id != message_input.conversation_id
            or original.origin is not message_input.origin
            or original.broadcast_recipient_id != message_input.broadcast_recipient_id
        ):
            raise InvalidWhatsAppMessageError("Retry target is not a valid message")
        if original.dispatch_state not in {
            WhatsAppDispatchState.DEFINITIVE_FAILED,
            WhatsAppDispatchState.UNKNOWN,
        }:
            raise InvalidWhatsAppMessageError(
                "Only failed or unknown messages can be explicitly resent"
            )

    def _validate_conversation(
        self,
        conversation: WhatsAppConversation,
    ) -> None:
        if (
            conversation.resolution_status
            is not WhatsAppConversationResolution.RESOLVED
            or conversation.customer_id is None
        ):
            raise WhatsAppConversationResolutionError(
                "Conversation identity must be resolved before replying"
            )
        customer = self._session.get(Customer, conversation.customer_id)
        if customer is None or customer.deleted_at is not None:
            raise WhatsAppConversationResolutionError(
                "Conversation customer is not available"
            )

    def _validate_user(self, user_id: int) -> None:
        user = self._session.get(User, user_id)
        if user is None:
            raise EntityNotFoundError("User", user_id)
        if not user.is_active:
            raise InactiveUserError(user_id)

    def _assert_same_payload(
        self,
        message: WhatsAppMessage,
        message_input: OutboundMessageInput,
    ) -> None:
        attachment = message.attachment
        existing_parameters = (
            tuple((item.name, item.value) for item in message.human_template_parameters)
            if message.origin is WhatsAppMessageOrigin.HUMAN
            else ()
        )
        incoming_parameters = (
            tuple((item.name, item.value) for item in message_input.template_parameters)
            if message_input.origin is WhatsAppMessageOrigin.HUMAN
            else ()
        )
        same_attachment = (
            message_input.attachment is None
            if attachment is None
            else message_input.attachment is not None
            and attachment.provider_media_id
            == message_input.attachment.provider_media_id
            and attachment.storage_key == message_input.attachment.storage_key
            and attachment.mime_type == message_input.attachment.mime_type
            and attachment.filename == message_input.attachment.filename
            and attachment.size_bytes == message_input.attachment.size_bytes
        )
        if not (
            message.conversation_id == message_input.conversation_id
            and message.sent_by_user_id == message_input.sent_by_user_id
            and message.message_type is message_input.message_type
            and message.body == message_input.body
            and message.retry_of_message_id == message_input.retry_of_message_id
            and message.origin is message_input.origin
            and message.broadcast_recipient_id == message_input.broadcast_recipient_id
            and message.template_name == message_input.template_name
            and message.template_language == message_input.template_language
            and existing_parameters == incoming_parameters
            and same_attachment
        ):
            raise WhatsAppIdempotencyConflictError(
                "Client-generated WhatsApp ID was reused with different data"
            )

    def _message_for_update(self, message_id: int) -> WhatsAppMessage:
        message = self._session.scalar(
            select(WhatsAppMessage)
            .where(WhatsAppMessage.id == message_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if message is None:
            raise EntityNotFoundError("WhatsAppMessage", message_id)
        return message

    def _recompute_broadcast_recipient(
        self,
        recipient: WhatsAppBroadcastRecipient | None,
        *,
        now: datetime,
    ) -> None:
        if recipient is None:
            return
        recompute_broadcast_recipient_projection(
            self._session,
            recipient,
            now=now,
        )

    def _message_graph_for_update(
        self,
        message_id: int,
    ) -> tuple[
        WhatsAppMessage,
        WhatsAppConversation,
        WhatsAppBroadcastRecipient | None,
    ]:
        discovered = self._session.get(WhatsAppMessage, message_id)
        if discovered is None:
            raise EntityNotFoundError("WhatsAppMessage", message_id)
        if discovered.broadcast_recipient_id is None:
            recipient = None
        else:
            recipient = self._session.scalar(
                select(WhatsAppBroadcastRecipient)
                .where(
                    WhatsAppBroadcastRecipient.id == discovered.broadcast_recipient_id
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if recipient is None:
                raise RuntimeError("Broadcast Message has no recipient")
        conversation = self._session.scalar(
            select(WhatsAppConversation)
            .where(WhatsAppConversation.id == discovered.conversation_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if conversation is None:
            raise RuntimeError("Persisted WhatsApp message has no conversation")
        message = self._message_for_update(message_id)
        return message, conversation, recipient

    def _conversation_for_message(
        self,
        message: WhatsAppMessage,
    ) -> WhatsAppConversation:
        conversation = self._session.scalar(
            select(WhatsAppConversation)
            .where(WhatsAppConversation.id == message.conversation_id)
            .with_for_update()
        )
        if conversation is None:
            raise RuntimeError("Persisted WhatsApp message has no conversation")
        return conversation

    def _result(self, message_id: int, *, created: bool) -> OutboundMessageResult:
        with self._session.begin():
            message = self._session.get(WhatsAppMessage, message_id)
            if message is None:
                raise EntityNotFoundError("WhatsAppMessage", message_id)
            return self._as_result(message, created=created)

    @staticmethod
    def _as_result(
        message: WhatsAppMessage,
        *,
        created: bool,
    ) -> OutboundMessageResult:
        if message.dispatch_state is None:
            raise RuntimeError("Outbound message has no dispatch state")
        return OutboundMessageResult(
            message_id=message.id,
            dispatch_state=message.dispatch_state,
            external_message_id=message.external_message_id,
            created=created,
        )

    @staticmethod
    def _normalize(
        message_input: OutboundMessageInput,
    ) -> OutboundMessageInput:
        body = WhatsAppMessageService._optional_text(message_input.body)
        attachment = message_input.attachment
        template_name = WhatsAppMessageService._optional_text(
            message_input.template_name
        )
        template_language = WhatsAppMessageService._optional_text(
            message_input.template_language
        )
        is_template = template_name is not None or template_language is not None
        if is_template and (template_name is None or template_language is None):
            raise InvalidWhatsAppMessageError("Template identity is incomplete")
        if message_input.origin is WhatsAppMessageOrigin.BROADCAST:
            if (
                message_input.broadcast_recipient_id is None
                or template_name is None
                or template_language is None
            ):
                raise InvalidWhatsAppMessageError(
                    "Broadcast outbound requires recipient and template identity"
                )
            if body is not None:
                raise InvalidWhatsAppMessageError(
                    "Broadcast template body is provider-owned"
                )
        else:
            if message_input.broadcast_recipient_id is not None:
                raise InvalidWhatsAppMessageError(
                    "Human outbound cannot reference a broadcast recipient"
                )
        if message_input.message_type is WhatsAppMessageType.TEXT:
            if (
                message_input.origin is WhatsAppMessageOrigin.HUMAN
                and not is_template
                and body is None
            ):
                raise InvalidWhatsAppMessageError("Text outbound requires a body")
            if attachment is not None and not is_template:
                raise InvalidWhatsAppMessageError(
                    "Text outbound cannot include an attachment"
                )
            if is_template and body is not None:
                raise InvalidWhatsAppMessageError("Template body is provider-owned")
        elif attachment is None:
            raise InvalidWhatsAppMessageError(
                "Media outbound requires attachment metadata"
            )
        if attachment is not None:
            provider_media_id = WhatsAppMessageService._optional_text(
                attachment.provider_media_id
            )
            storage_key = WhatsAppMessageService._optional_text(attachment.storage_key)
            mime_type = attachment.mime_type.strip()
            filename = WhatsAppMessageService._optional_text(attachment.filename)
            if provider_media_id is None and storage_key is None:
                raise InvalidWhatsAppMessageError(
                    "Media outbound requires a provider media ID or storage key"
                )
            if not mime_type:
                raise InvalidWhatsAppMessageError("Media MIME type is required")
            if attachment.size_bytes is not None and attachment.size_bytes < 0:
                raise InvalidWhatsAppMessageError("Media size cannot be negative")
            attachment = OutboundAttachmentInput(
                provider_media_id=provider_media_id,
                storage_key=storage_key,
                mime_type=mime_type,
                filename=filename,
                size_bytes=attachment.size_bytes,
                media_type=attachment.media_type,
            )
        return OutboundMessageInput(
            conversation_id=message_input.conversation_id,
            client_generated_id=message_input.client_generated_id,
            sent_by_user_id=message_input.sent_by_user_id,
            message_type=message_input.message_type,
            body=body,
            attachment=attachment,
            retry_of_message_id=message_input.retry_of_message_id,
            origin=message_input.origin,
            broadcast_recipient_id=message_input.broadcast_recipient_id,
            template_name=template_name,
            template_language=template_language,
            template_parameters=message_input.template_parameters,
        )

    @staticmethod
    def _optional_text(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _aware_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Datetime must be timezone-aware")
        return value.astimezone(UTC)
