from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    User,
    WhatsAppConversation,
    WhatsAppDirection,
    WhatsAppDispatchState,
    WhatsAppMessage,
    WhatsAppMessageStatusEvent,
    WhatsAppMessageType,
    WhatsAppProviderState,
)
from app.services import (
    InboundMessageInput,
    OutboundAttachmentInput,
    OutboundMessageInput,
    ProviderStatusInput,
    WhatsAppConversationService,
    WhatsAppIdempotencyConflictError,
    WhatsAppInboundService,
    WhatsAppMessageService,
    WhatsAppStatusService,
)
from app.services.errors import (
    InvalidWhatsAppMessageError,
    WhatsAppReplyInProgressError,
)
from app.whatsapp import FakeWhatsAppProvider, ProviderErrorKind

NOW = datetime(2030, 8, 10, 18, 0, tzinfo=UTC)


def fake_provider() -> FakeWhatsAppProvider:
    return FakeWhatsAppProvider(now=NOW, freeform_window=timedelta(hours=24))


def create_conversation(
    db_session: Session,
    provider: FakeWhatsAppProvider,
    *,
    external_id: str = "inbound-outbound-test",
) -> WhatsAppConversation:
    result = WhatsAppInboundService(db_session, provider).receive(
        InboundMessageInput(
            external_message_id=external_id,
            external_phone="+54 11 6000 1234",
            provider_contact_id=None,
            display_name="Cliente outbound",
            message_type=WhatsAppMessageType.TEXT,
            body="Hola",
            provider_message_at=NOW,
        ),
        now=NOW,
    )
    conversation = db_session.get(WhatsAppConversation, result.conversation_id)
    if conversation is None:
        raise AssertionError("Conversation was not persisted")
    db_session.commit()
    return conversation


def outbound(
    conversation_id: int,
    user_id: int,
    client_id: UUID,
    *,
    body: str | None = "Respuesta humana",
    message_type: WhatsAppMessageType = WhatsAppMessageType.TEXT,
    attachment: OutboundAttachmentInput | None = None,
    retry_of_message_id: int | None = None,
) -> OutboundMessageInput:
    return OutboundMessageInput(
        conversation_id=conversation_id,
        client_generated_id=client_id,
        sent_by_user_id=user_id,
        message_type=message_type,
        body=body,
        attachment=attachment,
        retry_of_message_id=retry_of_message_id,
    )


def test_outbound_acceptance_is_idempotent_and_resolves_waiting(
    db_session: Session,
    supervisor_user: User,
) -> None:
    provider = fake_provider()
    conversation = create_conversation(db_session, provider)
    service = WhatsAppMessageService(db_session, provider)
    request = outbound(
        conversation.id,
        supervisor_user.id,
        UUID("00000000-0000-0000-0000-000000000001"),
    )

    sent = service.send(request, now=NOW + timedelta(minutes=1))
    replay = service.send(request, now=NOW + timedelta(minutes=2))

    assert sent.dispatch_state is WhatsAppDispatchState.ACCEPTED
    assert sent.external_message_id == "fake-message-000001"
    assert replay.message_id == sent.message_id
    assert replay.created is False
    assert len(provider.requests) == 1
    message = db_session.get(WhatsAppMessage, sent.message_id)
    refreshed = db_session.get(WhatsAppConversation, conversation.id)
    assert message is not None
    assert message.provider_state is WhatsAppProviderState.SENT
    assert message.sent_at == NOW
    assert refreshed is not None
    assert refreshed.waiting_for_response is False
    assert refreshed.waiting_since_at is None
    assert refreshed.unread_count == 1
    db_session.commit()

    read = WhatsAppConversationService(db_session).mark_as_read(
        conversation.id,
        now=NOW + timedelta(minutes=3),
    )
    assert read.unread_count == 0


def test_outbound_idempotency_conflict_does_not_send_twice(
    db_session: Session,
    supervisor_user: User,
) -> None:
    provider = fake_provider()
    conversation = create_conversation(
        db_session,
        provider,
        external_id="inbound-idempotency-conflict",
    )
    service = WhatsAppMessageService(db_session, provider)
    client_id = UUID("00000000-0000-0000-0000-000000000002")
    service.send(outbound(conversation.id, supervisor_user.id, client_id), now=NOW)

    with pytest.raises(WhatsAppIdempotencyConflictError):
        service.send(
            outbound(
                conversation.id,
                supervisor_user.id,
                client_id,
                body="Payload distinto",
            ),
            now=NOW,
        )
    assert len(provider.requests) == 1


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        (ProviderErrorKind.PERMANENT_FAILURE, WhatsAppDispatchState.DEFINITIVE_FAILED),
        (ProviderErrorKind.RETRYABLE_FAILURE, WhatsAppDispatchState.DEFINITIVE_FAILED),
        (
            ProviderErrorKind.TIMEOUT_BEFORE_ACCEPTANCE,
            WhatsAppDispatchState.DEFINITIVE_FAILED,
        ),
        (
            ProviderErrorKind.TIMEOUT_UNKNOWN_ACCEPTANCE,
            WhatsAppDispatchState.UNKNOWN,
        ),
    ],
)
def test_provider_failures_reconcile_dispatch_state(
    db_session: Session,
    supervisor_user: User,
    kind: ProviderErrorKind,
    expected: WhatsAppDispatchState,
) -> None:
    provider = fake_provider()
    conversation = create_conversation(
        db_session,
        provider,
        external_id=f"inbound-error-{kind.value}",
    )
    client_id = UUID(
        "00000000-0000-0000-0000-000000000010"
        if expected is WhatsAppDispatchState.UNKNOWN
        else "00000000-0000-0000-0000-000000000011"
    )
    provider.configure_error(client_id, kind, code="SAFE_CODE")

    result = WhatsAppMessageService(db_session, provider).send(
        outbound(conversation.id, supervisor_user.id, client_id),
        now=NOW,
    )

    assert result.dispatch_state is expected
    message = db_session.get(WhatsAppMessage, result.message_id)
    refreshed = db_session.get(WhatsAppConversation, conversation.id)
    assert message is not None
    assert message.provider_error_code == "SAFE_CODE"
    assert message.provider_error_message == "Fake provider failure"
    assert refreshed is not None
    assert refreshed.waiting_for_response is True


def test_unknown_is_not_automatically_retried_but_explicit_resend_is_allowed(
    db_session: Session,
    supervisor_user: User,
) -> None:
    provider = fake_provider()
    conversation = create_conversation(
        db_session,
        provider,
        external_id="inbound-unknown-retry",
    )
    original_client_id = UUID("00000000-0000-0000-0000-000000000020")
    provider.configure_error(
        original_client_id,
        ProviderErrorKind.TIMEOUT_UNKNOWN_ACCEPTANCE,
    )
    service = WhatsAppMessageService(db_session, provider)
    conversation_id = conversation.id
    user_id = supervisor_user.id
    original = service.send(
        outbound(conversation_id, user_id, original_client_id),
        now=NOW,
    )

    with pytest.raises(WhatsAppReplyInProgressError):
        service.send(
            outbound(
                conversation_id,
                user_id,
                UUID("00000000-0000-0000-0000-000000000021"),
            ),
            now=NOW,
        )

    retry = service.send(
        outbound(
            conversation_id,
            user_id,
            UUID("00000000-0000-0000-0000-000000000022"),
            retry_of_message_id=original.message_id,
        ),
        now=NOW,
    )
    assert original.dispatch_state is WhatsAppDispatchState.UNKNOWN
    assert retry.dispatch_state is WhatsAppDispatchState.ACCEPTED
    assert len(provider.requests) == 2


def test_status_events_are_deduplicated_and_reconciled_out_of_order(
    db_session: Session,
    supervisor_user: User,
) -> None:
    provider = fake_provider()
    conversation = create_conversation(
        db_session,
        provider,
        external_id="inbound-status-order",
    )
    sent = WhatsAppMessageService(db_session, provider).send(
        outbound(
            conversation.id,
            supervisor_user.id,
            UUID("00000000-0000-0000-0000-000000000030"),
        ),
        now=NOW,
    )
    if sent.external_message_id is None:
        raise AssertionError("Fake provider did not return an external ID")
    service = WhatsAppStatusService(db_session)
    read_at = NOW + timedelta(minutes=4)
    delivered_at = NOW + timedelta(minutes=3)

    read = service.record(
        ProviderStatusInput(
            external_message_id=sent.external_message_id,
            state=WhatsAppProviderState.READ,
            occurred_at=read_at,
        ),
        received_at=NOW + timedelta(minutes=5),
    )
    delivered = service.record(
        ProviderStatusInput(
            external_message_id=sent.external_message_id,
            state=WhatsAppProviderState.DELIVERED,
            occurred_at=delivered_at,
        ),
        received_at=NOW + timedelta(minutes=6),
    )
    duplicate = service.record(
        ProviderStatusInput(
            external_message_id=sent.external_message_id,
            state=WhatsAppProviderState.READ,
            occurred_at=read_at,
        ),
        received_at=NOW + timedelta(minutes=7),
    )

    assert read.created is True
    assert delivered.created is True
    assert duplicate.created is False
    assert duplicate.event_id == read.event_id
    message = db_session.get(WhatsAppMessage, sent.message_id)
    assert message is not None
    assert message.provider_state is WhatsAppProviderState.READ
    assert message.provider_status_at == read_at
    assert message.delivered_at == delivered_at
    assert message.read_at == read_at
    assert (
        db_session.scalar(
            select(func.count(WhatsAppMessageStatusEvent.id)).where(
                WhatsAppMessageStatusEvent.message_id == sent.message_id
            )
        )
        == 2
    )
    db_session.rollback()

    service.record(
        ProviderStatusInput(
            external_message_id=sent.external_message_id,
            state=WhatsAppProviderState.FAILED,
            occurred_at=read_at + timedelta(minutes=1),
            error_code="STALE_FAILURE",
        ),
        received_at=read_at + timedelta(minutes=2),
    )
    message = db_session.get(WhatsAppMessage, sent.message_id)
    assert message is not None
    assert message.provider_state is WhatsAppProviderState.READ


def test_status_before_provider_response_is_attached_on_acceptance(
    db_session: Session,
    supervisor_user: User,
) -> None:
    provider = fake_provider()
    conversation = create_conversation(
        db_session,
        provider,
        external_id="inbound-status-before-response",
    )
    status = WhatsAppStatusService(db_session).record(
        ProviderStatusInput(
            external_message_id="fake-message-000001",
            state=WhatsAppProviderState.DELIVERED,
            occurred_at=NOW + timedelta(seconds=5),
        ),
        received_at=NOW,
    )
    assert status.message_id is None

    sent = WhatsAppMessageService(db_session, provider).send(
        outbound(
            conversation.id,
            supervisor_user.id,
            UUID("00000000-0000-0000-0000-000000000040"),
        ),
        now=NOW,
    )

    event = db_session.get(WhatsAppMessageStatusEvent, status.event_id)
    message = db_session.get(WhatsAppMessage, sent.message_id)
    assert event is not None
    assert event.message_id == sent.message_id
    assert message is not None
    assert message.provider_state is WhatsAppProviderState.DELIVERED


def test_failed_delivery_restores_waiting_for_response(
    db_session: Session,
    supervisor_user: User,
) -> None:
    provider = fake_provider()
    conversation = create_conversation(
        db_session,
        provider,
        external_id="inbound-delivery-failed",
    )
    sent = WhatsAppMessageService(db_session, provider).send(
        outbound(
            conversation.id,
            supervisor_user.id,
            UUID("00000000-0000-0000-0000-000000000050"),
        ),
        now=NOW,
    )
    if sent.external_message_id is None:
        raise AssertionError("Expected provider external ID")

    WhatsAppStatusService(db_session).record(
        ProviderStatusInput(
            external_message_id=sent.external_message_id,
            state=WhatsAppProviderState.FAILED,
            occurred_at=NOW + timedelta(minutes=1),
            error_code="UNDELIVERABLE",
            error_message="Safe failure",
        ),
        received_at=NOW + timedelta(minutes=1),
    )

    refreshed = db_session.get(WhatsAppConversation, conversation.id)
    assert refreshed is not None
    assert refreshed.waiting_for_response is True
    assert refreshed.waiting_since_at == NOW


def test_late_inbound_webhook_before_last_response_does_not_reopen_waiting(
    db_session: Session,
    supervisor_user: User,
) -> None:
    provider = fake_provider()
    conversation = create_conversation(
        db_session,
        provider,
        external_id="inbound-before-late-webhook",
    )
    provider.set_now(NOW + timedelta(minutes=1))
    WhatsAppMessageService(db_session, provider).send(
        outbound(
            conversation.id,
            supervisor_user.id,
            UUID("00000000-0000-0000-0000-000000000055"),
        ),
        now=NOW + timedelta(minutes=1),
    )

    WhatsAppInboundService(db_session, provider).receive(
        InboundMessageInput(
            external_message_id="late-webhook-with-old-time",
            external_phone=conversation.external_phone,
            provider_contact_id=None,
            display_name=None,
            message_type=WhatsAppMessageType.TEXT,
            body="Mensaje anterior demorado",
            provider_message_at=NOW + timedelta(seconds=30),
        ),
        now=NOW + timedelta(minutes=2),
    )

    refreshed = db_session.get(WhatsAppConversation, conversation.id)
    assert refreshed is not None
    assert refreshed.waiting_for_response is False


def test_media_outbound_records_attachment_and_request(
    db_session: Session,
    supervisor_user: User,
) -> None:
    provider = fake_provider()
    conversation = create_conversation(
        db_session,
        provider,
        external_id="inbound-media-outbound",
    )
    result = WhatsAppMessageService(db_session, provider).send(
        outbound(
            conversation.id,
            supervisor_user.id,
            UUID("00000000-0000-0000-0000-000000000060"),
            body="Plano",
            message_type=WhatsAppMessageType.DOCUMENT,
            attachment=OutboundAttachmentInput(
                provider_media_id=None,
                storage_key="stored-document-1",
                mime_type="application/pdf",
                filename="plano.pdf",
                size_bytes=500,
            ),
        ),
        now=NOW,
    )

    assert result.dispatch_state is WhatsAppDispatchState.ACCEPTED
    message = db_session.get(WhatsAppMessage, result.message_id)
    assert message is not None
    assert message.direction is WhatsAppDirection.OUTBOUND
    assert message.attachment is not None
    assert message.attachment.storage_key == "stored-document-1"


def test_closed_window_and_invalid_media_are_rejected(
    db_session: Session,
    supervisor_user: User,
) -> None:
    open_provider = fake_provider()
    conversation = create_conversation(
        db_session,
        open_provider,
        external_id="inbound-validation",
    )
    closed_provider = FakeWhatsAppProvider(now=NOW, freeform_window=None)
    service = WhatsAppMessageService(db_session, closed_provider)
    assert service.can_send_freeform(conversation.id, now=NOW) is False
    db_session.rollback()
    with pytest.raises(InvalidWhatsAppMessageError):
        service.send(
            outbound(
                conversation.id,
                supervisor_user.id,
                UUID("00000000-0000-0000-0000-000000000070"),
            ),
            now=NOW,
        )

    with pytest.raises(InvalidWhatsAppMessageError):
        outbound_request = outbound(
            conversation.id,
            supervisor_user.id,
            UUID("00000000-0000-0000-0000-000000000071"),
            message_type=WhatsAppMessageType.IMAGE,
        )
        WhatsAppMessageService(db_session, open_provider).send(
            outbound_request,
            now=NOW,
        )
