from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.core.security import create_access_token
from app.main import create_app
from app.models import (
    Customer,
    LeadSource,
    Opportunity,
    OpportunityStatus,
    User,
    UserRole,
    WhatsAppConversation,
    WhatsAppConversationOpportunity,
    WhatsAppConversationResolution,
)
from app.schemas.whatsapp import (
    ConversationChangePageResponse,
    ConversationDetailResponse,
    ConversationPageResponse,
    FakeInboundResponse,
    FakeStatusSequenceResponse,
    MediaUploadResponse,
    MessageChangePageResponse,
    MessagePageResponse,
    OutboundMessageResponse,
)
from app.whatsapp import (
    FakeMediaStorage,
    FakeWhatsAppProvider,
    FilesystemMediaStorage,
    ProviderMediaPayload,
    ProviderMediaReference,
    ProviderSendResult,
    ProviderTemplateSnapshot,
    SendDocumentRequest,
    SendImageRequest,
    SendTemplateRequest,
    SendTextRequest,
    WhatsAppMediaPolicy,
    WindowDecision,
    WindowEvaluationContext,
)
from app.whatsapp.runtime import WhatsAppRuntime, build_fake_whatsapp_runtime

_NOW = datetime.now(UTC).replace(microsecond=0)


@dataclass(frozen=True, slots=True)
class WhatsAppApiContext:
    client: TestClient
    runtime: WhatsAppRuntime
    provider: FakeWhatsAppProvider


@pytest.fixture
def whatsapp_api(
    db_session: Session,
    supervisor_user: User,
) -> Iterator[WhatsAppApiContext]:
    provider = FakeWhatsAppProvider(
        now=_NOW + timedelta(minutes=1),
        freeform_window=timedelta(hours=24),
    )
    runtime = build_fake_whatsapp_runtime(provider=provider)
    application = create_app(runtime)

    def override_db_session() -> Iterator[Session]:
        try:
            yield db_session
        finally:
            if db_session.in_transaction():
                db_session.commit()

    application.dependency_overrides[get_db_session] = override_db_session
    with TestClient(application) as client:
        client.headers["Authorization"] = (
            f"Bearer {create_access_token(supervisor_user.id)}"
        )
        yield WhatsAppApiContext(client, runtime, provider)


def test_all_whatsapp_routes_require_active_authentication(
    whatsapp_api: WhatsAppApiContext,
    db_session: Session,
) -> None:
    authorization = whatsapp_api.client.headers.pop("Authorization")
    try:
        assert whatsapp_api.client.get("/api/whatsapp/conversations").status_code == 401
        assert (
            whatsapp_api.client.post(
                "/api/whatsapp/media",
                files={"file": ("a.pdf", b"pdf", "application/pdf")},
                data={"metadata": '{"media_type":"DOCUMENT"}'},
            ).status_code
            == 401
        )
        assert (
            whatsapp_api.client.post(
                "/api/whatsapp/dev/inbound",
                json=_text_inbound_payload("unauthenticated"),
            ).status_code
            == 401
        )
        assert (
            whatsapp_api.client.get(
                f"/api/whatsapp/media/{uuid4()}/content"
            ).status_code
            == 401
        )
        assert (
            whatsapp_api.client.get(
                "/api/whatsapp/attachments/999999/content"
            ).status_code
            == 401
        )
    finally:
        whatsapp_api.client.headers["Authorization"] = authorization

    inactive = User(
        full_name="Usuario inactivo WhatsApp",
        email="inactive-whatsapp@faa.test",
        password_hash="not-used",
        role=UserRole.VENDEDOR,
        is_active=False,
    )
    db_session.add(inactive)
    db_session.commit()
    response = whatsapp_api.client.get(
        "/api/whatsapp/conversations",
        headers={"Authorization": f"Bearer {create_access_token(inactive.id)}"},
    )
    assert response.status_code == 401


def test_conversation_list_filters_detail_and_cursor_validation(
    whatsapp_api: WhatsAppApiContext,
) -> None:
    first = _inject_text(
        whatsapp_api,
        external_id="wamid.api.alpha",
        phone="+54 11 6000-0001",
        display_name="Constructora Alpha API",
    )
    _inject_text(
        whatsapp_api,
        external_id="wamid.api.beta",
        phone="+54 11 6000-0002",
        display_name="Beta API",
    )

    response = whatsapp_api.client.get(
        "/api/whatsapp/conversations",
        params={"limit": 1, "search": " alpha api ", "waiting_only": True},
    )
    assert response.status_code == 200
    page = ConversationPageResponse.model_validate(response.json())
    assert [item.id for item in page.items] == [first.message.conversation_id]
    assert page.items[0].unread_count == 1
    assert page.items[0].waiting_for_response is True
    assert page.items[0].can_send_freeform is True
    assert page.items[0].template_required is False
    assert page.sync_cursor

    detail_response = whatsapp_api.client.get(
        f"/api/whatsapp/conversations/{first.message.conversation_id}"
    )
    detail = ConversationDetailResponse.model_validate(detail_response.json())
    assert detail_response.status_code == 200
    assert detail.customer is not None
    assert detail.active_opportunity is not None
    assert detail.opportunity_links[0].is_active is True
    assert "storage_key" not in detail_response.text
    assert "provider_media_id" not in detail_response.text

    malformed = whatsapp_api.client.get(
        "/api/whatsapp/conversations",
        params={"page_cursor": "not-a-valid-cursor"},
    )
    assert malformed.status_code == 422
    assert set(malformed.json()) == {"detail"}

    first_page = ConversationPageResponse.model_validate(
        whatsapp_api.client.get(
            "/api/whatsapp/conversations",
            params={"limit": 1},
        ).json()
    )
    assert first_page.next_page_cursor is not None
    second_page = ConversationPageResponse.model_validate(
        whatsapp_api.client.get(
            "/api/whatsapp/conversations",
            params={"limit": 1, "page_cursor": first_page.next_page_cursor},
        ).json()
    )
    assert {item.id for item in first_page.items}.isdisjoint(
        item.id for item in second_page.items
    )
    cursor_payload, cursor_signature = first_page.next_page_cursor.split(
        ".", maxsplit=1
    )
    tampered_signature = (
        "A" if cursor_signature[0] != "A" else "B"
    ) + cursor_signature[1:]
    tampered_cursor = f"{cursor_payload}.{tampered_signature}"
    assert (
        whatsapp_api.client.get(
            "/api/whatsapp/conversations",
            params={"page_cursor": tampered_cursor},
        ).status_code
        == 422
    )


def test_conversation_polling_observes_read_filter_exit(
    whatsapp_api: WhatsAppApiContext,
) -> None:
    inbound = _inject_text(
        whatsapp_api,
        external_id="wamid.api.polling",
        phone="+54 11 6000-0010",
    )
    initial = ConversationPageResponse.model_validate(
        whatsapp_api.client.get("/api/whatsapp/conversations").json()
    )

    read_response = whatsapp_api.client.post(
        f"/api/whatsapp/conversations/{inbound.message.conversation_id}/read"
    )
    assert read_response.status_code == 200
    assert read_response.json()["unread_count"] == 0
    assert read_response.json()["waiting_for_response"] is True

    changes_response = whatsapp_api.client.get(
        "/api/whatsapp/conversations/changes",
        params={"cursor": initial.sync_cursor},
    )
    changes = ConversationChangePageResponse.model_validate(changes_response.json())
    assert changes_response.status_code == 200
    assert inbound.message.conversation_id in {item.id for item in changes.items}
    assert changes.next_cursor


def test_conversation_change_polling_pages_without_skips(
    whatsapp_api: WhatsAppApiContext,
) -> None:
    initial = ConversationPageResponse.model_validate(
        whatsapp_api.client.get("/api/whatsapp/conversations").json()
    )
    first = _inject_text(
        whatsapp_api,
        external_id="wamid.api.change-page.1",
        phone="+54 11 6000-0011",
    )
    second = _inject_text(
        whatsapp_api,
        external_id="wamid.api.change-page.2",
        phone="+54 11 6000-0012",
    )

    first_page = ConversationChangePageResponse.model_validate(
        whatsapp_api.client.get(
            "/api/whatsapp/conversations/changes",
            params={"cursor": initial.sync_cursor, "limit": 1},
        ).json()
    )
    second_page = ConversationChangePageResponse.model_validate(
        whatsapp_api.client.get(
            "/api/whatsapp/conversations/changes",
            params={"cursor": first_page.next_cursor, "limit": 1},
        ).json()
    )

    assert first_page.has_more is True
    assert {item.id for item in first_page.items + second_page.items} == {
        first.message.conversation_id,
        second.message.conversation_id,
    }


def test_message_history_change_polling_status_and_duplicate_events(
    whatsapp_api: WhatsAppApiContext,
) -> None:
    first = _inject_text(
        whatsapp_api,
        external_id="wamid.api.history.1",
        phone="+54 11 6000-0020",
    )
    _inject_text(
        whatsapp_api,
        external_id="wamid.api.history.2",
        phone="+54 11 6000-0020",
        provider_message_at=_NOW + timedelta(seconds=1),
    )
    messages_url = (
        f"/api/whatsapp/conversations/{first.message.conversation_id}/messages"
    )
    newest = MessagePageResponse.model_validate(
        whatsapp_api.client.get(messages_url, params={"limit": 1}).json()
    )
    assert len(newest.items) == 1
    assert newest.next_before_cursor is not None
    older = MessagePageResponse.model_validate(
        whatsapp_api.client.get(
            messages_url,
            params={"limit": 1, "before_cursor": newest.next_before_cursor},
        ).json()
    )
    assert len(older.items) == 1
    assert newest.items[0].id != older.items[0].id

    outbound = _send_text(whatsapp_api, first.message.conversation_id)
    status_response = whatsapp_api.client.post(
        f"/api/whatsapp/dev/messages/{outbound.message.id}/statuses",
        json={
            "events": [
                {
                    "state": "READ",
                    "occurred_at": (_NOW + timedelta(minutes=5)).isoformat(),
                },
                {
                    "state": "DELIVERED",
                    "occurred_at": (_NOW + timedelta(minutes=4)).isoformat(),
                },
            ],
            "duplicate": True,
        },
    )
    statuses = FakeStatusSequenceResponse.model_validate(status_response.json())
    assert status_response.status_code == 200
    assert any(not item.created for item in statuses.results)
    assert statuses.message.status.provider_state is not None
    assert statuses.message.status.provider_state.value == "READ"

    changes_response = whatsapp_api.client.get(
        f"{messages_url}/changes",
        params={"cursor": newest.sync_cursor},
    )
    changes = MessageChangePageResponse.model_validate(changes_response.json())
    assert changes_response.status_code == 200
    assert outbound.message.id in {item.id for item in changes.items}
    assert "provider_payload" not in changes_response.text


def test_text_send_idempotency_and_documented_http_outcomes(
    whatsapp_api: WhatsAppApiContext,
) -> None:
    inbound = _inject_text(
        whatsapp_api,
        external_id="wamid.api.send",
        phone="+54 11 6000-0030",
    )
    client_id = uuid4()
    payload = {
        "message_type": "TEXT",
        "client_generated_id": str(client_id),
        "body": "Respuesta API",
    }
    url = f"/api/whatsapp/conversations/{inbound.message.conversation_id}/messages"

    created = whatsapp_api.client.post(url, json=payload)
    replay = whatsapp_api.client.post(url, json=payload)
    conflict = whatsapp_api.client.post(url, json={**payload, "body": "Otro texto"})

    assert created.status_code == 201
    assert replay.status_code == 200
    assert conflict.status_code == 409
    assert len(whatsapp_api.provider.requests) == 1
    result = OutboundMessageResponse.model_validate(created.json())
    assert result.message.sent_by is not None
    assert result.message.client_generated_id == client_id
    assert result.message.status.dispatch_state is not None
    assert result.can_send_freeform is True


@pytest.mark.parametrize(
    ("behavior", "expected_status", "dispatch_state"),
    [
        ("PERMANENT_FAILURE", 200, "DEFINITIVE_FAILED"),
        ("RETRYABLE_FAILURE", 200, "DEFINITIVE_FAILED"),
        ("TIMEOUT_BEFORE_ACCEPTANCE", 200, "DEFINITIVE_FAILED"),
        ("TIMEOUT_UNKNOWN_ACCEPTANCE", 202, "UNKNOWN"),
    ],
)
def test_fake_provider_failure_and_timeout_modes(
    whatsapp_api: WhatsAppApiContext,
    behavior: str,
    expected_status: int,
    dispatch_state: str,
) -> None:
    inbound = _inject_text(
        whatsapp_api,
        external_id=f"wamid.api.behavior.{behavior}",
        phone=f"+54 11 61{len(behavior):02d}-0040",
    )
    client_id = uuid4()
    configured = whatsapp_api.client.put(
        f"/api/whatsapp/dev/provider-behaviors/{client_id}",
        json={
            "kind": behavior,
            "code": "SAFE_FAKE_CODE",
            "safe_message": "Safe simulated provider failure",
        },
    )
    response = whatsapp_api.client.post(
        f"/api/whatsapp/conversations/{inbound.message.conversation_id}/messages",
        json={
            "message_type": "TEXT",
            "client_generated_id": str(client_id),
            "body": "Respuesta con falla",
        },
    )

    assert configured.status_code == 200
    assert response.status_code == expected_status
    parsed = OutboundMessageResponse.model_validate(response.json())
    assert parsed.message.status.dispatch_state is not None
    assert parsed.message.status.dispatch_state.value == dispatch_state
    assert parsed.message.status.error_code == "SAFE_FAKE_CODE"
    if behavior == "TIMEOUT_UNKNOWN_ACCEPTANCE":
        retry_response = whatsapp_api.client.post(
            f"/api/whatsapp/conversations/{inbound.message.conversation_id}/messages",
            json={
                "message_type": "TEXT",
                "client_generated_id": str(uuid4()),
                "body": "Reenvío explícito",
                "retry_of_message_id": parsed.message.id,
            },
        )
        retry = OutboundMessageResponse.model_validate(retry_response.json())
        assert retry_response.status_code == 201
        assert retry.message.retry_of_message_id == parsed.message.id
        assert retry.message.is_retry is True
        assert len(whatsapp_api.provider.requests) == 2


@pytest.mark.parametrize(
    ("media_type", "filename", "mime_type", "content"),
    [
        ("IMAGE", "../foto.jpg", "image/jpeg", b"\xff\xd8\xfffake-image"),
        ("DOCUMENT", "../ficha.pdf", "application/pdf", b"%PDF-fake"),
    ],
)
def test_authenticated_media_upload_preview_and_outbound_send(
    whatsapp_api: WhatsAppApiContext,
    media_type: str,
    filename: str,
    mime_type: str,
    content: bytes,
) -> None:
    inbound = _inject_text(
        whatsapp_api,
        external_id=f"wamid.api.media.{media_type}",
        phone=f"+54 11 6000-01{len(media_type):02d}",
    )
    upload_response = whatsapp_api.client.post(
        "/api/whatsapp/media",
        files={"file": (filename, content, mime_type)},
        data={"metadata": f'{{"media_type":"{media_type}"}}'},
    )
    uploaded = MediaUploadResponse.model_validate(upload_response.json())

    assert upload_response.status_code == 201
    assert uploaded.filename is not None
    assert ".." not in uploaded.filename
    assert "storage_key" not in upload_response.text
    assert "fake-media" not in upload_response.text
    preview = whatsapp_api.client.get(uploaded.content_url)
    assert preview.status_code == 200
    assert preview.content == content
    assert preview.headers["cache-control"] == "private, no-store"

    sent_response = whatsapp_api.client.post(
        f"/api/whatsapp/conversations/{inbound.message.conversation_id}/messages",
        json={
            "message_type": media_type,
            "client_generated_id": str(uuid4()),
            "media_ref": str(uploaded.media_ref),
            "caption": "Archivo solicitado",
        },
    )
    sent = OutboundMessageResponse.model_validate(sent_response.json())
    assert sent_response.status_code == 201
    assert sent.message.attachment is not None
    content_url = sent.message.attachment.content_url
    assert content_url is not None
    persisted_content = whatsapp_api.client.get(content_url)
    assert persisted_content.content == content
    assert "storage_key" not in sent_response.text


def test_media_validation_and_strict_requests(whatsapp_api: WhatsAppApiContext) -> None:
    invalid_mime = whatsapp_api.client.post(
        "/api/whatsapp/media",
        files={"file": ("bad.exe", b"bad", "application/octet-stream")},
        data={"metadata": '{"media_type":"DOCUMENT"}'},
    )
    extra_metadata = whatsapp_api.client.post(
        "/api/whatsapp/media",
        files={"file": ("a.pdf", b"pdf", "application/pdf")},
        data={"metadata": '{"media_type":"DOCUMENT","extra":true}'},
    )
    mismatched_content = whatsapp_api.client.post(
        "/api/whatsapp/media",
        files={"file": ("fake.jpg", b"%PDF-1.7 fake", "image/jpeg")},
        data={"metadata": '{"media_type":"IMAGE"}'},
    )
    assert invalid_mime.status_code == 422
    assert extra_metadata.status_code == 422
    assert mismatched_content.status_code == 422

    inbound = _inject_text(
        whatsapp_api,
        external_id="wamid.api.strict",
        phone="+54 11 6000-0050",
    )
    strict_send = whatsapp_api.client.post(
        f"/api/whatsapp/conversations/{inbound.message.conversation_id}/messages",
        json={
            "message_type": "TEXT",
            "client_generated_id": str(uuid4()),
            "body": "Texto",
            "sent_by_user_id": 999,
        },
    )
    assert strict_send.status_code == 422
    missing_media = whatsapp_api.client.post(
        f"/api/whatsapp/conversations/{inbound.message.conversation_id}/messages",
        json={
            "message_type": "IMAGE",
            "client_generated_id": str(uuid4()),
            "media_ref": str(uuid4()),
        },
    )
    assert missing_media.status_code == 422
    assert set(missing_media.json()) == {"detail"}


def test_media_size_limit_is_enforced_before_storage(
    db_session: Session,
    supervisor_user: User,
) -> None:
    provider = FakeWhatsAppProvider(freeform_window=timedelta(hours=24))
    runtime = build_fake_whatsapp_runtime(provider=provider)
    constrained_runtime = replace(
        runtime,
        media_policy=WhatsAppMediaPolicy(
            image_max_bytes=3,
            document_max_bytes=3,
            image_mime_types=runtime.media_policy.image_mime_types,
            document_mime_types=runtime.media_policy.document_mime_types,
        ),
    )
    with _client_for_runtime(
        db_session, supervisor_user, constrained_runtime
    ) as client:
        response = client.post(
            "/api/whatsapp/media",
            files={"file": ("large.pdf", b"four", "application/pdf")},
            data={"metadata": '{"media_type":"DOCUMENT"}'},
        )
    assert response.status_code == 422


def test_storage_failure_returns_safe_error_without_media_reference(
    db_session: Session,
    supervisor_user: User,
) -> None:
    storage = FakeMediaStorage()
    storage.configure_put_failure("Internal storage path failed")
    runtime = build_fake_whatsapp_runtime(storage=storage)

    with _client_for_runtime(db_session, supervisor_user, runtime) as client:
        response = client.post(
            "/api/whatsapp/media",
            files={"file": ("falla.pdf", b"%PDF-1.7 failure", "application/pdf")},
            data={"metadata": '{"media_type":"DOCUMENT"}'},
        )

    assert response.status_code == 422
    assert set(response.json()) == {"detail"}
    assert "media_ref" not in response.text
    assert "path" not in response.text.lower()


def test_uploaded_media_reference_survives_backend_runtime_restart(
    db_session: Session,
    supervisor_user: User,
    tmp_path: Path,
) -> None:
    provider = FakeWhatsAppProvider(freeform_window=timedelta(hours=24))
    first_runtime = build_fake_whatsapp_runtime(
        provider=provider,
        storage=FilesystemMediaStorage(tmp_path),
    )
    with _client_for_runtime(db_session, supervisor_user, first_runtime) as client:
        upload_response = client.post(
            "/api/whatsapp/media",
            files={
                "file": (
                    "persistente.pdf",
                    b"%PDF-1.7 persistent",
                    "application/pdf",
                )
            },
            data={"metadata": '{"media_type":"DOCUMENT"}'},
        )
        uploaded = MediaUploadResponse.model_validate(upload_response.json())

    restarted_runtime = build_fake_whatsapp_runtime(
        provider=provider,
        storage=FilesystemMediaStorage(tmp_path),
    )
    with _client_for_runtime(db_session, supervisor_user, restarted_runtime) as client:
        preview = client.get(uploaded.content_url)

    assert upload_response.status_code == 201
    assert preview.status_code == 200
    assert preview.content == b"%PDF-1.7 persistent"
    assert str(tmp_path) not in upload_response.text
    assert "storage_key" not in upload_response.text


def test_soft_deleted_commercial_entities_do_not_remove_media_history(
    whatsapp_api: WhatsAppApiContext,
    db_session: Session,
) -> None:
    inbound = _inject_text(
        whatsapp_api,
        external_id="wamid.api.retained-media",
        phone="+54 11 6000-0055",
    )
    uploaded = _upload_document(whatsapp_api, b"%PDF-1.7 retained")
    sent_response = whatsapp_api.client.post(
        f"/api/whatsapp/conversations/{inbound.message.conversation_id}/messages",
        json={
            "message_type": "DOCUMENT",
            "client_generated_id": str(uuid4()),
            "media_ref": str(uploaded.media_ref),
        },
    )
    sent = OutboundMessageResponse.model_validate(sent_response.json())
    detail = ConversationDetailResponse.model_validate(
        whatsapp_api.client.get(
            f"/api/whatsapp/conversations/{inbound.message.conversation_id}"
        ).json()
    )
    assert sent.message.attachment is not None
    content_url = sent.message.attachment.content_url
    assert content_url is not None
    assert detail.customer is not None
    assert detail.active_opportunity is not None

    deleted_at = datetime.now(UTC)
    customer = db_session.get(Customer, detail.customer.id)
    opportunity = db_session.get(Opportunity, detail.active_opportunity.id)
    assert customer is not None
    assert opportunity is not None
    customer.deleted_at = deleted_at
    opportunity.deleted_at = deleted_at
    db_session.commit()

    content = whatsapp_api.client.get(content_url)
    assert content.status_code == 200
    assert content.content == b"%PDF-1.7 retained"


def test_fake_inbound_media_downloads_through_attachment_endpoint(
    whatsapp_api: WhatsAppApiContext,
) -> None:
    content = b"%PDF-inbound"
    uploaded = _upload_document(whatsapp_api, content)
    injected_response = whatsapp_api.client.post(
        "/api/whatsapp/dev/inbound",
        json={
            "message_type": "DOCUMENT",
            "external_message_id": "wamid.api.inbound.document",
            "external_phone": "+54 11 6000-0060",
            "display_name": "Inbound documento",
            "caption": "Adjunto",
            "media_ref": str(uploaded.media_ref),
            "provider_message_at": _NOW.isoformat(),
        },
    )
    injected = FakeInboundResponse.model_validate(injected_response.json())
    assert injected_response.status_code == 201
    assert injected.message.attachment is not None
    assert injected.message.attachment.is_available is False

    content_response = whatsapp_api.client.get(
        f"/api/whatsapp/attachments/{injected.message.attachment.id}/content"
    )
    assert content_response.status_code == 200
    assert content_response.content == content

    repeated_response = whatsapp_api.client.post(
        "/api/whatsapp/dev/inbound",
        json={
            "message_type": "DOCUMENT",
            "external_message_id": "wamid.api.inbound.document",
            "external_phone": "+54 11 6000-0060",
            "display_name": "Inbound documento",
            "caption": "Adjunto",
            "media_ref": str(uploaded.media_ref),
            "provider_message_at": _NOW.isoformat(),
        },
    )
    repeated = FakeInboundResponse.model_validate(repeated_response.json())
    assert repeated_response.status_code == 200
    assert repeated.created is False
    assert repeated.message.id == injected.message.id


def test_existing_customer_links_replace_unlink_and_preserve_history(
    whatsapp_api: WhatsAppApiContext,
    db_session: Session,
    supervisor_user: User,
) -> None:
    customer = Customer(
        name="Cliente existente API",
        phone="+54 (11) 6000-0070",
    )
    other_customer = Customer(name="Otro cliente", phone="+54 11 6999-9999")
    db_session.add_all((customer, other_customer))
    db_session.flush()
    first_opportunity = _opportunity(customer.id, OpportunityStatus.NUEVA)
    second_opportunity = _opportunity(customer.id, OpportunityStatus.NEGOCIACION)
    wrong_opportunity = _opportunity(other_customer.id, OpportunityStatus.NUEVA)
    db_session.add_all((first_opportunity, second_opportunity, wrong_opportunity))
    db_session.flush()
    first_opportunity_id = first_opportunity.id
    second_opportunity_id = second_opportunity.id
    wrong_opportunity_id = wrong_opportunity.id
    db_session.commit()
    before_count = db_session.scalar(select(func.count()).select_from(Opportunity))
    db_session.commit()

    inbound = _inject_text(
        whatsapp_api,
        external_id="wamid.api.existing",
        phone="+54 11 6000-0070",
    )
    detail_url = f"/api/whatsapp/conversations/{inbound.message.conversation_id}"
    initial = ConversationDetailResponse.model_validate(
        whatsapp_api.client.get(detail_url).json()
    )
    assert initial.active_opportunity is None
    assert {item.id for item in initial.opportunity_suggestions} == {
        first_opportunity_id,
        second_opportunity_id,
    }
    after_inbound_count = db_session.scalar(
        select(func.count()).select_from(Opportunity)
    )
    db_session.commit()
    assert after_inbound_count == before_count

    link_url = f"{detail_url}/opportunity-link"
    linked = whatsapp_api.client.put(
        link_url,
        json={"opportunity_id": first_opportunity_id},
    )
    repeated = whatsapp_api.client.put(
        link_url,
        json={"opportunity_id": first_opportunity_id},
    )
    wrong = whatsapp_api.client.put(
        link_url,
        json={"opportunity_id": wrong_opportunity_id},
    )
    assert linked.status_code == repeated.status_code == 200
    assert wrong.status_code == 409

    first_opportunity.status = OpportunityStatus.GANADA
    first_opportunity.updated_at = datetime.now(UTC)
    db_session.commit()
    replaced_response = whatsapp_api.client.put(
        link_url,
        json={"opportunity_id": second_opportunity_id},
    )
    replaced = ConversationDetailResponse.model_validate(replaced_response.json())
    assert replaced.active_opportunity is not None
    assert replaced.active_opportunity.id == second_opportunity_id
    assert len(replaced.opportunity_links) == 2
    assert any(
        link.opportunity.id == first_opportunity_id and not link.is_active
        for link in replaced.opportunity_links
    )

    unlinked = ConversationDetailResponse.model_validate(
        whatsapp_api.client.delete(link_url).json()
    )
    repeated_unlink = whatsapp_api.client.delete(link_url)
    assert unlinked.active_opportunity is None
    assert len(unlinked.opportunity_links) == 2
    assert repeated_unlink.status_code == 200
    assert (
        db_session.scalar(
            select(func.count()).select_from(WhatsAppConversationOpportunity)
        )
        == 2
    )
    assert supervisor_user.id > 0


def test_closed_window_and_identity_review_return_conflicts(
    db_session: Session,
    supervisor_user: User,
) -> None:
    provider = FakeWhatsAppProvider(now=_NOW, freeform_window=None)
    runtime = build_fake_whatsapp_runtime(provider=provider)
    with _client_for_runtime(db_session, supervisor_user, runtime) as client:
        inbound = _inject_text_client(
            client,
            external_id="wamid.api.closed",
            phone="+54 11 6000-0080",
        )
        detail = client.get(
            f"/api/whatsapp/conversations/{inbound.message.conversation_id}"
        )
        assert detail.json()["can_send_freeform"] is False
        assert detail.json()["template_required"] is True
        assert detail.json()["reason"] == "APPROVED_TEMPLATE_REQUIRED"
        send = client.post(
            f"/api/whatsapp/conversations/{inbound.message.conversation_id}/messages",
            json={
                "message_type": "TEXT",
                "client_generated_id": str(uuid4()),
                "body": "Fuera de ventana",
            },
        )
        assert send.status_code == 409
        assert "template" in send.json()["detail"].lower()

    unresolved = WhatsAppConversation(
        customer_id=None,
        external_phone="+54 11 6000-0081",
        phone_match_key="+541160000081",
        resolution_status=WhatsAppConversationResolution.NEEDS_REVIEW,
    )
    db_session.add(unresolved)
    db_session.commit()
    open_provider = FakeWhatsAppProvider(
        now=_NOW,
        freeform_window=timedelta(hours=24),
    )
    open_runtime = build_fake_whatsapp_runtime(provider=open_provider)
    with _client_for_runtime(db_session, supervisor_user, open_runtime) as client:
        response = client.post(
            f"/api/whatsapp/conversations/{unresolved.id}/messages",
            json={
                "message_type": "TEXT",
                "client_generated_id": str(uuid4()),
                "body": "No debe enviarse",
            },
        )
        assert response.status_code == 409
        assert open_provider.requests == []


def test_missing_resources_use_documented_not_found(
    whatsapp_api: WhatsAppApiContext,
) -> None:
    assert (
        whatsapp_api.client.get("/api/whatsapp/conversations/999999").status_code == 404
    )
    assert (
        whatsapp_api.client.get(
            "/api/whatsapp/conversations/999999/messages"
        ).status_code
        == 404
    )
    assert (
        whatsapp_api.client.get("/api/whatsapp/attachments/999999/content").status_code
        == 404
    )


def test_dev_routes_are_absent_for_non_fake_provider(
    db_session: Session,
    supervisor_user: User,
) -> None:
    fake = FakeWhatsAppProvider(freeform_window=timedelta(hours=24))
    runtime = build_fake_whatsapp_runtime(provider=fake)
    non_fake_runtime = replace(runtime, provider=DelegatingWhatsAppProvider(fake))

    with _client_for_runtime(db_session, supervisor_user, non_fake_runtime) as client:
        response = client.post(
            "/api/whatsapp/dev/inbound",
            json=_text_inbound_payload("route-must-not-exist"),
        )
        assert response.status_code == 404
        assert client.get("/api/whatsapp/conversations").status_code == 200


class DelegatingWhatsAppProvider:
    def __init__(self, delegate: FakeWhatsAppProvider) -> None:
        self._delegate = delegate

    def send_text(self, request: SendTextRequest) -> ProviderSendResult:
        return self._delegate.send_text(request)

    def send_image(self, request: SendImageRequest) -> ProviderSendResult:
        return self._delegate.send_image(request)

    def send_document(self, request: SendDocumentRequest) -> ProviderSendResult:
        return self._delegate.send_document(request)

    def send_template(self, request: SendTemplateRequest) -> ProviderSendResult:
        return self._delegate.send_template(request)

    def download_media(
        self,
        reference: ProviderMediaReference,
    ) -> ProviderMediaPayload:
        return self._delegate.download_media(reference)

    def list_templates(self) -> tuple[ProviderTemplateSnapshot, ...]:
        return self._delegate.list_templates()

    def evaluate_window(
        self,
        context: WindowEvaluationContext,
    ) -> WindowDecision:
        return self._delegate.evaluate_window(context)


def _inject_text(
    context: WhatsAppApiContext,
    *,
    external_id: str,
    phone: str,
    display_name: str = "Contacto API",
    provider_message_at: datetime = _NOW,
) -> FakeInboundResponse:
    return _inject_text_client(
        context.client,
        external_id=external_id,
        phone=phone,
        display_name=display_name,
        provider_message_at=provider_message_at,
    )


def _inject_text_client(
    client: TestClient,
    *,
    external_id: str,
    phone: str,
    display_name: str = "Contacto API",
    provider_message_at: datetime = _NOW,
) -> FakeInboundResponse:
    response = client.post(
        "/api/whatsapp/dev/inbound",
        json={
            "message_type": "TEXT",
            "external_message_id": external_id,
            "external_phone": phone,
            "display_name": display_name,
            "body": "Consulta de WhatsApp",
            "provider_message_at": provider_message_at.isoformat(),
        },
    )
    assert response.status_code in {200, 201}
    return FakeInboundResponse.model_validate(response.json())


def _send_text(
    context: WhatsAppApiContext,
    conversation_id: int,
) -> OutboundMessageResponse:
    response = context.client.post(
        f"/api/whatsapp/conversations/{conversation_id}/messages",
        json={
            "message_type": "TEXT",
            "client_generated_id": str(uuid4()),
            "body": "Respuesta de FAA",
        },
    )
    assert response.status_code == 201
    return OutboundMessageResponse.model_validate(response.json())


def _upload_document(
    context: WhatsAppApiContext,
    content: bytes,
) -> MediaUploadResponse:
    response = context.client.post(
        "/api/whatsapp/media",
        files={"file": ("documento.pdf", content, "application/pdf")},
        data={"metadata": '{"media_type":"DOCUMENT"}'},
    )
    assert response.status_code == 201
    return MediaUploadResponse.model_validate(response.json())


def _opportunity(customer_id: int, status: OpportunityStatus) -> Opportunity:
    return Opportunity(
        customer_id=customer_id,
        source=LeadSource.WHATSAPP,
        status=status,
        current_status_entered_at=_NOW,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _text_inbound_payload(suffix: str) -> dict[str, str]:
    return {
        "message_type": "TEXT",
        "external_message_id": f"wamid.api.{suffix}",
        "external_phone": "+54 11 6555-0000",
        "display_name": "Contacto API",
        "body": "Consulta",
        "provider_message_at": _NOW.isoformat(),
    }


def _client_for_runtime(
    db_session: Session,
    user: User,
    runtime: WhatsAppRuntime,
) -> TestClient:
    application = create_app(runtime)

    def override_db_session() -> Iterator[Session]:
        try:
            yield db_session
        finally:
            if db_session.in_transaction():
                db_session.commit()

    application.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(application)
    client.headers["Authorization"] = f"Bearer {create_access_token(user.id)}"
    return client
