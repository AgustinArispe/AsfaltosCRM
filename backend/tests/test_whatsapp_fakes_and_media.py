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
    MediaStorageError,
    ProviderErrorKind,
    ProviderMediaPayload,
    ProviderMediaReference,
    ProviderRecipient,
    ProviderTemplateSnapshot,
    SendDocumentRequest,
    SendImageRequest,
    SendTemplateRequest,
    SendTextRequest,
    StoreMediaRequest,
    TemplateHeaderType,
    TemplateParameter,
    WhatsAppProviderError,
    WindowEvaluationContext,
)

NOW = datetime(2030, 8, 11, 12, 0, tzinfo=UTC)


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


def test_fake_media_storage_round_trip_delete_and_failure() -> None:
    storage = FakeMediaStorage()
    request = StoreMediaRequest(
        content=b"image-bytes",
        mime_type="image/png",
        filename="mapa.png",
    )
    stored = storage.store(request)

    assert stored.storage_key == "fake-media-000001"
    assert stored.size_bytes == len(b"image-bytes")
    assert storage.read(stored.storage_key).content == b"image-bytes"
    storage.delete(stored.storage_key)
    with pytest.raises(FileNotFoundError):
        storage.read(stored.storage_key)

    storage.configure_store_failure("Storage unavailable")
    with pytest.raises(MediaStorageError, match="Storage unavailable"):
        storage.store(request)
    storage.configure_store_failure(None)
    assert storage.store(request).storage_key == "fake-media-000002"


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
            content=b"pdf bytes",
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
    service = WhatsAppMediaService(db_session, provider, storage)

    first = service.download(attachment.id, now=NOW)
    second = service.download(attachment.id, now=NOW + timedelta(minutes=1))

    assert first.storage_status is WhatsAppStorageStatus.AVAILABLE
    assert second.storage_key == first.storage_key
    persisted = db_session.get(WhatsAppAttachment, attachment.id)
    assert persisted is not None
    assert persisted.mime_type == "application/pdf"
    assert persisted.filename == "informe.pdf"
    assert persisted.size_bytes == len(b"pdf bytes")
    assert persisted.storage_key is not None
    assert storage.read(persisted.storage_key).content == b"pdf bytes"


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
                content=b"bytes",
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
        storage.configure_store_failure("Safe storage failure")

    result = WhatsAppMediaService(db_session, provider, storage).download(
        attachment.id,
        now=NOW,
    )

    assert result.storage_status is WhatsAppStorageStatus.FAILED
    persisted = db_session.get(WhatsAppAttachment, attachment.id)
    assert persisted is not None
    assert persisted.storage_key is None
    assert persisted.storage_error is not None
