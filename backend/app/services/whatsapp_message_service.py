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
    WhatsAppConversation,
    WhatsAppConversationResolution,
    WhatsAppDirection,
    WhatsAppDispatchState,
    WhatsAppMessage,
    WhatsAppMessageType,
    WhatsAppProviderState,
    WhatsAppStorageStatus,
)
from app.services.errors import (
    EntityNotFoundError,
    InactiveUserError,
    InvalidWhatsAppMessageError,
    WhatsAppConversationResolutionError,
    WhatsAppIdempotencyConflictError,
    WhatsAppReplyInProgressError,
)
from app.services.whatsapp_projection_service import (
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
    SendTextRequest,
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


@dataclass(frozen=True, slots=True)
class OutboundMessageInput:
    conversation_id: int
    client_generated_id: UUID
    sent_by_user_id: int
    message_type: WhatsAppMessageType
    body: str | None
    attachment: OutboundAttachmentInput | None = None
    retry_of_message_id: int | None = None


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

        with self._session.begin():
            message = self._message_for_update(message_id)
            if message.dispatch_state is not WhatsAppDispatchState.PENDING:
                return self._as_result(message, created=created)
            message.dispatch_state = WhatsAppDispatchState.IN_PROGRESS
            message.updated_at = later_datetime(message.updated_at, requested_at)
            provider_request = self._build_provider_request(message)
            self._session.flush()

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
            conversation = self._session.scalar(
                select(WhatsAppConversation)
                .where(WhatsAppConversation.id == message_input.conversation_id)
                .with_for_update()
            )
            if conversation is None:
                raise EntityNotFoundError(
                    "WhatsAppConversation",
                    message_input.conversation_id,
                )
            self._validate_conversation(conversation)
            self._validate_user(message_input.sent_by_user_id)
            decision = self._provider.evaluate_window(
                WindowEvaluationContext(
                    last_inbound_at=conversation.last_inbound_at,
                    now=requested_at,
                )
            )
            conversation.window_expires_at = decision.window_expires_at
            if not decision.can_send_freeform:
                raise InvalidWhatsAppMessageError(
                    "Freeform WhatsApp window is closed; an approved template is required"
                )

            existing = self._session.scalar(
                select(WhatsAppMessage)
                .where(
                    WhatsAppMessage.client_generated_id
                    == message_input.client_generated_id
                )
                .with_for_update()
            )
            if existing is not None:
                self._assert_same_payload(existing, message_input)
                return (
                    existing.id,
                    False,
                    existing.dispatch_state is WhatsAppDispatchState.PENDING,
                )

            self._validate_retry(message_input)
            active_reply = self._session.scalar(
                select(WhatsAppMessage.id)
                .where(
                    WhatsAppMessage.conversation_id == conversation.id,
                    WhatsAppMessage.direction == WhatsAppDirection.OUTBOUND,
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
                body=message_input.body,
                sent_by_user_id=message_input.sent_by_user_id,
                retry_of_message_id=message_input.retry_of_message_id,
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
                        media_type=message_input.message_type,
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
            message = self._message_for_update(message_id)
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
            conversation = self._conversation_for_message(message)
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
            message = self._message_for_update(message_id)
            if message.dispatch_state is WhatsAppDispatchState.IN_PROGRESS:
                message.dispatch_state = (
                    WhatsAppDispatchState.UNKNOWN
                    if error.details.acceptance_unknown
                    else WhatsAppDispatchState.DEFINITIVE_FAILED
                )
                message.provider_error_code = error.details.code
                message.provider_error_message = error.details.safe_message
                message.updated_at = later_datetime(
                    message.updated_at,
                    reconciled_at,
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
        )
        if message is None:
            raise EntityNotFoundError("WhatsAppMessage", message_id)
        return message

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
        if message_input.message_type is WhatsAppMessageType.TEXT:
            if body is None:
                raise InvalidWhatsAppMessageError("Text outbound requires a body")
            if attachment is not None:
                raise InvalidWhatsAppMessageError(
                    "Text outbound cannot include an attachment"
                )
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
            )
        return OutboundMessageInput(
            conversation_id=message_input.conversation_id,
            client_generated_id=message_input.client_generated_id,
            sent_by_user_id=message_input.sent_by_user_id,
            message_type=message_input.message_type,
            body=body,
            attachment=attachment,
            retry_of_message_id=message_input.retry_of_message_id,
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
