from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    WhatsAppAttachment,
    WhatsAppMessageType,
    WhatsAppProviderState,
    WhatsAppStorageStatus,
)
from app.services import (
    InboundAttachmentInput,
    InboundMessageInput,
    WhatsAppInboundService,
    WhatsAppMediaService,
)
from app.whatsapp import (
    FakeMediaStorage,
    FakeWhatsAppProvider,
    MediaPutRequest,
    MediaStorageConflictError,
    MediaStorageError,
    MediaStorageNotFoundError,
    ProviderErrorKind,
    ProviderMediaPayload,
    ProviderMediaReference,
    ProviderRecipient,
    ProviderTemplateSnapshot,
    SendDocumentRequest,
    SendImageRequest,
    SendTemplateRequest,
    SendTextRequest,
    StoredMedia,
    TemplateHeaderType,
    TemplateParameter,
    WhatsAppMediaPolicy,
    WhatsAppProviderError,
    WindowEvaluationContext,
)

NOW = datetime(2030, 8, 11, 12, 0, tzinfo=UTC)
MEDIA_POLICY = WhatsAppMediaPolicy(
    image_max_bytes=1024,
    document_max_bytes=1024,
    image_mime_types=frozenset({"image/jpeg", "image/png", "image/webp"}),
    document_mime_types=frozenset({"application/pdf"}),
)


def test_fake_provider_records_all_requests_and_has_deterministic_ids() -> None:
    template = ProviderTemplateSnapshot(
        external_id="template-1",
        name="seguimiento",
        language="es_AR",
        category="UTILITY",
        status="APPROVED",
        header_type=TemplateHeaderType.NONE,
    )
    provider = FakeWhatsAppProvider(
        now=NOW,
        freeform_window=timedelta(hours=24),
        templates=(template,),
    )
    recipient = ProviderRecipient(phone="+541100000000")
    media = ProviderMediaReference(
        provider_media_id="media-1",
        storage_key=None,
        mime_type="image/jpeg",
        filename="foto.jpg",
    )

    results = (
        provider.send_text(
            SendTextRequest(
                recipient=recipient,
                client_generated_id=UUID("10000000-0000-0000-0000-000000000001"),
                text="Hola",
            )
        ),
        provider.send_image(
            SendImageRequest(
                recipient=recipient,
                client_generated_id=UUID("10000000-0000-0000-0000-000000000002"),
                media=media,
                caption=None,
            )
        ),
        provider.send_document(
            SendDocumentRequest(
                recipient=recipient,
                client_generated_id=UUID("10000000-0000-0000-0000-000000000003"),
                media=media,
                caption="Adjunto",
            )
        ),
        provider.send_template(
            SendTemplateRequest(
                recipient=recipient,
                client_generated_id=UUID("10000000-0000-0000-0000-000000000004"),
                template_name="seguimiento",
                language="es_AR",
                parameters=(TemplateParameter(name="nombre", value="FAA"),),
            )
        ),
    )

    assert tuple(result.external_message_id for result in results) == (
        "fake-message-000001",
        "fake-message-000002",
        "fake-message-000003",
        "fake-message-000004",
    )
    assert len(provider.requests) == 4
    assert provider.list_templates() == (template,)
    provider.set_templates(())
    assert provider.list_templates() == ()
    assert (
        provider.evaluate_window(
            WindowEvaluationContext(
                last_inbound_at=NOW - timedelta(hours=1),
                now=NOW,
            )
        ).can_send_freeform
        is True
    )


def test_fake_provider_supports_media_errors_and_delivery_event_scenarios() -> None:
    provider = FakeWhatsAppProvider(now=NOW, freeform_window=None)
    payload = ProviderMediaPayload(
        content=b"content",
        mime_type="application/pdf",
        filename="ficha.pdf",
    )
    provider.add_media("media-pdf", payload)
    reference = ProviderMediaReference(
        provider_media_id="media-pdf",
        storage_key=None,
        mime_type=None,
        filename=None,
    )
    assert provider.download_media(reference) == payload
    assert (
        provider.evaluate_window(
            WindowEvaluationContext(last_inbound_at=NOW, now=NOW)
        ).can_send_freeform
        is False
    )

    events = provider.emit_delivery_events(
        "external-1",
        (WhatsAppProviderState.READ, WhatsAppProviderState.DELIVERED),
        duplicate=True,
        occurred_at=NOW,
    )
    assert len(events) == 4
    assert events[0].state is WhatsAppProviderState.READ
    assert events[1].state is WhatsAppProviderState.DELIVERED
    assert len(provider.delivery_events) == 4

    client_id = UUID("20000000-0000-0000-0000-000000000001")
    provider.configure_error(
        client_id,
        ProviderErrorKind.TIMEOUT_UNKNOWN_ACCEPTANCE,
        code="TIMEOUT",
        safe_message="Unknown acceptance",
    )
    with pytest.raises(WhatsAppProviderError) as captured:
        provider.send_text(
            SendTextRequest(
                recipient=ProviderRecipient(phone="123"),
                client_generated_id=client_id,
                text="test",
            )
        )
    assert captured.value.details.acceptance_unknown is True
    assert captured.value.details.retryable is True

    with pytest.raises(WhatsAppProviderError):
        provider.download_media(
            ProviderMediaReference(
                provider_media_id="missing",
                storage_key=None,
                mime_type=None,
                filename=None,
            )
        )


def test_fake_media_storage_round_trip_idempotency_conflict_and_failure() -> None:
    storage = FakeMediaStorage()
    media_ref = UUID("30000000-0000-0000-0000-000000000001")
    request = MediaPutRequest(
        media_ref=media_ref,
        content=b"\x89PNG\r\n\x1a\nimage-bytes",
        media_type=WhatsAppMessageType.IMAGE,
        mime_type="image/png",
        filename="mapa.png",
    )
    stored = storage.put(request)

    assert stored.storage_key == "fake-media-000001"
    assert stored.size_bytes == len(request.content)
    assert storage.get(stored.storage_key).content == request.content
    assert storage.get_metadata(media_ref) == stored
    assert storage.put(request) == stored
    with pytest.raises(MediaStorageConflictError):
        storage.put(
            MediaPutRequest(
                media_ref=media_ref,
                content=request.content + b"changed",
                media_type=request.media_type,
                mime_type=request.mime_type,
                filename=request.filename,
            )
        )
    with pytest.raises(MediaStorageNotFoundError):
        storage.get("missing")

    storage.configure_put_failure("Storage unavailable")
    with pytest.raises(MediaStorageError, match="Storage unavailable"):
        storage.put(
            MediaPutRequest(
                media_ref=UUID("30000000-0000-0000-0000-000000000002"),
                content=request.content,
                media_type=request.media_type,
                mime_type=request.mime_type,
                filename=request.filename,
            )
        )


def create_pending_attachment(
    db_session: Session,
    provider: FakeWhatsAppProvider,
    external_id: str,
    provider_media_id: str,
) -> WhatsAppAttachment:
    result = WhatsAppInboundService(db_session, provider).receive(
        InboundMessageInput(
            external_message_id=external_id,
            external_phone=f"+5411{external_id[-8:]}",
            provider_contact_id=None,
            display_name="Cliente media",
            message_type=WhatsAppMessageType.DOCUMENT,
            body="Documento",
            provider_message_at=NOW,
            attachment=InboundAttachmentInput(
                provider_media_id=provider_media_id,
                mime_type=None,
                filename=None,
                size_bytes=None,
            ),
        ),
        now=NOW,
    )
    attachment = db_session.scalar(
        select(WhatsAppAttachment).where(
            WhatsAppAttachment.message_id == result.message_id
        )
    )
    if attachment is None:
        raise AssertionError("Attachment was not persisted")
    db_session.commit()
    return attachment


def test_media_service_downloads_once_and_persists_stable_storage_metadata(
    db_session: Session,
) -> None:
    provider = FakeWhatsAppProvider(now=NOW, freeform_window=timedelta(hours=24))
    provider.add_media(
        "provider-doc-1",
        ProviderMediaPayload(
            content=b"%PDF-1.7 pdf bytes",
            mime_type="application/pdf",
            filename="informe.pdf",
        ),
    )
    attachment = create_pending_attachment(
        db_session,
        provider,
        "media-download-00000001",
        "provider-doc-1",
    )
    storage = FakeMediaStorage()
    service = WhatsAppMediaService(db_session, provider, storage, MEDIA_POLICY)

    first = service.download(attachment.id, now=NOW)
    second = service.download(attachment.id, now=NOW + timedelta(minutes=1))

    assert first.storage_status is WhatsAppStorageStatus.AVAILABLE
    assert second.storage_key == first.storage_key
    persisted = db_session.get(WhatsAppAttachment, attachment.id)
    assert persisted is not None
    assert persisted.mime_type == "application/pdf"
    assert persisted.filename == "informe.pdf"
    assert persisted.size_bytes == len(b"%PDF-1.7 pdf bytes")
    assert persisted.storage_key is not None
    assert storage.get(persisted.storage_key).content == b"%PDF-1.7 pdf bytes"


@pytest.mark.parametrize("storage_failure", [False, True])
def test_media_service_records_safe_provider_or_storage_failure(
    db_session: Session,
    *,
    storage_failure: bool,
) -> None:
    provider = FakeWhatsAppProvider(now=NOW, freeform_window=timedelta(hours=24))
    media_id = "provider-doc-storage" if storage_failure else "provider-doc-missing"
    if storage_failure:
        provider.add_media(
            media_id,
            ProviderMediaPayload(
                content=b"%PDF-1.7 bytes",
                mime_type="application/pdf",
                filename=None,
            ),
        )
    attachment = create_pending_attachment(
        db_session,
        provider,
        f"media-failure-{int(storage_failure):08d}",
        media_id,
    )
    storage = FakeMediaStorage()
    if storage_failure:
        storage.configure_put_failure("Safe storage failure")

    service = WhatsAppMediaService(
        db_session,
        provider,
        storage,
        MEDIA_POLICY,
    )
    result = service.download(attachment.id, now=NOW)

    assert result.storage_status is WhatsAppStorageStatus.FAILED
    if storage_failure:
        storage.configure_put_failure(None)
        retried = service.download(attachment.id, now=NOW + timedelta(minutes=1))
        not_downgraded = service.mark_storage_failed(
            attachment.id,
            "Late failure",
            expected_storage_key="superseded-storage-key",
            now=NOW + timedelta(minutes=2),
        )
        assert retried.storage_status is WhatsAppStorageStatus.AVAILABLE
        assert not_downgraded.storage_status is WhatsAppStorageStatus.AVAILABLE
        assert retried.storage_key is not None
        current_failure = service.mark_storage_failed(
            attachment.id,
            "Integrity failure",
            expected_storage_key=retried.storage_key,
            now=NOW + timedelta(minutes=3),
        )
        recovered = service.download(
            attachment.id,
            now=NOW + timedelta(minutes=4),
        )
        assert current_failure.storage_status is WhatsAppStorageStatus.FAILED
        assert recovered.storage_status is WhatsAppStorageStatus.AVAILABLE
    persisted = db_session.get(WhatsAppAttachment, attachment.id)
    assert persisted is not None
    if storage_failure:
        assert persisted.storage_key is not None
        assert persisted.storage_error is None
    else:
        assert persisted.storage_key is None
        assert persisted.storage_error is not None


def test_media_service_recovers_when_storage_succeeds_before_db_failure(
    db_session: Session,
) -> None:
    provider = FakeWhatsAppProvider(now=NOW, freeform_window=timedelta(hours=24))
    provider.add_media(
        "provider-doc-db-failure",
        ProviderMediaPayload(
            content=b"%PDF-1.7 durable-before-db",
            mime_type="application/pdf",
            filename="durable.pdf",
        ),
    )
    attachment = create_pending_attachment(
        db_session,
        provider,
        "media-db-failure-00000001",
        "provider-doc-db-failure",
    )
    storage = RecordingFakeMediaStorage()
    failing_service = FailingReconciliationMediaService(
        db_session,
        provider,
        storage,
        MEDIA_POLICY,
    )

    with pytest.raises(RuntimeError, match="Injected DB reconciliation failure"):
        failing_service.download(attachment.id, now=NOW)

    pending = db_session.get(WhatsAppAttachment, attachment.id)
    assert pending is not None
    assert pending.storage_status is WhatsAppStorageStatus.PENDING
    assert pending.storage_key is None
    assert len(storage.put_results) == 1
    db_session.commit()

    recovered = WhatsAppMediaService(
        db_session,
        provider,
        storage,
        MEDIA_POLICY,
    ).download(attachment.id, now=NOW + timedelta(minutes=1))

    assert recovered.storage_status is WhatsAppStorageStatus.AVAILABLE
    assert len(storage.put_results) == 2
    assert storage.put_results[0].storage_key != storage.put_results[1].storage_key


class RecordingFakeMediaStorage(FakeMediaStorage):
    def __init__(self) -> None:
        super().__init__()
        self.put_results: list[StoredMedia] = []

    def put(self, request: MediaPutRequest) -> StoredMedia:
        result = super().put(request)
        self.put_results.append(result)
        return result


class FailingReconciliationMediaService(WhatsAppMediaService):
    def _attachment_for_update(self, attachment_id: int) -> WhatsAppAttachment:
        del attachment_id
        raise RuntimeError("Injected DB reconciliation failure")
