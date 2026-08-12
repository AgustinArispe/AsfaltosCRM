from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.core.security import create_access_token, hash_password
from app.main import create_app
from app.models import (
    Customer,
    Opportunity,
    User,
    UserRole,
    WhatsAppBroadcast,
    WhatsAppBroadcastRecipient,
    WhatsAppBroadcastRecipientStatus,
    WhatsAppBroadcastStatus,
    WhatsAppConsentDecision,
    WhatsAppConsentSource,
    WhatsAppConversation,
    WhatsAppDispatchState,
    WhatsAppMarketingConsentEvent,
    WhatsAppMessage,
    WhatsAppMessageOrigin,
    WhatsAppMessageType,
)
from app.schemas.whatsapp_broadcast import (
    BroadcastResponse,
    BroadcastValidationResponse,
    ConsentEventResultResponse,
)
from app.whatsapp import (
    FakeMediaStorage,
    FakeWhatsAppProvider,
    MediaPutRequest,
    ProviderErrorKind,
    ProviderTemplateSnapshot,
    SendTemplateRequest,
    TemplateHeaderType,
)
from app.whatsapp.runtime import build_fake_whatsapp_runtime


@dataclass(frozen=True, slots=True)
class BroadcastContext:
    client: TestClient
    provider: FakeWhatsAppProvider
    storage: FakeMediaStorage
    now: datetime


@pytest.fixture
def broadcast_context(
    db_session: Session,
    supervisor_user: User,
) -> Iterator[BroadcastContext]:
    now = datetime.now(UTC).replace(microsecond=0)
    provider = FakeWhatsAppProvider(
        now=now,
        templates=(
            ProviderTemplateSnapshot(
                external_id="marketing-1",
                name="oferta_asfalto",
                language="es_AR",
                category="MARKETING",
                status="APPROVED",
                header_type=TemplateHeaderType.NONE,
                parameter_names=("fecha",),
            ),
            ProviderTemplateSnapshot(
                external_id="utility-1",
                name="seguimiento",
                language="es_AR",
                category="UTILITY",
                status="APPROVED",
                header_type=TemplateHeaderType.NONE,
            ),
            ProviderTemplateSnapshot(
                external_id="unsupported-1",
                name="carrusel",
                language="es_AR",
                category="MARKETING",
                status="APPROVED",
                header_type=TemplateHeaderType.NONE,
                supported_for_send=False,
            ),
        ),
    )
    storage = FakeMediaStorage()
    runtime = build_fake_whatsapp_runtime(provider=provider, storage=storage)
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
        yield BroadcastContext(client, provider, storage, now)


def test_broadcast_happy_path_is_explicit_idempotent_and_auditable(
    broadcast_context: BroadcastContext,
    db_session: Session,
) -> None:
    context = broadcast_context
    inbound = context.client.post(
        "/api/whatsapp/dev/inbound",
        json={
            "message_type": "TEXT",
            "external_message_id": "wamid.broadcast.inbound",
            "external_phone": "+54 11 6100-0001",
            "display_name": "Cliente Broadcast",
            "body": "Consulta pendiente",
            "provider_message_at": (context.now - timedelta(minutes=5)).isoformat(),
        },
    )
    assert inbound.status_code == 201
    conversation_id = inbound.json()["message"]["conversation_id"]
    conversation = db_session.get(WhatsAppConversation, conversation_id)
    assert conversation is not None
    assert conversation.customer_id is not None
    customer_id = conversation.customer_id
    opportunities_before = db_session.scalar(select(func.count(Opportunity.id)))
    db_session.commit()

    consent_id = uuid4()
    consent_payload = {
        "client_event_id": str(consent_id),
        "customer_id": customer_id,
        "decision": "OPT_IN",
        "source": "FAA_CRM",
        "occurred_at": (context.now - timedelta(minutes=4)).isoformat(),
    }
    consent = context.client.post(
        "/api/whatsapp/marketing-consent-events",
        json=consent_payload,
    )
    replayed_consent = context.client.post(
        "/api/whatsapp/marketing-consent-events",
        json=consent_payload,
    )
    assert consent.status_code == 201
    assert replayed_consent.status_code == 200
    assert replayed_consent.json()["created"] is False
    assert replayed_consent.json()["event"]["id"] == consent.json()["event"]["id"]

    templates = context.client.get("/api/whatsapp/broadcast-templates")
    assert templates.status_code == 200
    assert [item["external_id"] for item in templates.json()] == ["marketing-1"]

    create_id = uuid4()
    create_payload = {
        "client_generated_id": str(create_id),
        "label": " Oferta agosto ",
        "external_campaign_reference": "MKT-2026-08",
        "template_external_id": "marketing-1",
        "parameters": [{"name": "fecha", "value": "31/08"}],
    }
    created = context.client.post("/api/whatsapp/broadcasts", json=create_payload)
    replayed_create = context.client.post(
        "/api/whatsapp/broadcasts", json=create_payload
    )
    assert created.status_code == 201
    assert replayed_create.status_code == 200
    assert replayed_create.json()["id"] == created.json()["id"]
    broadcast_id = created.json()["id"]

    create_conflict = context.client.post(
        "/api/whatsapp/broadcasts",
        json={**create_payload, "label": "Otro contenido"},
    )
    assert create_conflict.status_code == 409

    selection_command = uuid4()
    selection_payload = {
        "command_id": str(selection_command),
        "customer_ids": [customer_id, customer_id],
        "expected_version": 1,
    }
    selected = context.client.put(
        f"/api/whatsapp/broadcasts/{broadcast_id}/recipients",
        json=selection_payload,
    )
    assert selected.status_code == 200
    assert selected.json()["selected_count"] == 1
    assert selected.json()["duplicate_customer_ids"] == [customer_id]
    assert selected.json()["missing_consent_customer_ids"] == []
    version = selected.json()["version"]
    replayed_selection = context.client.put(
        f"/api/whatsapp/broadcasts/{broadcast_id}/recipients",
        json=selection_payload,
    )
    assert replayed_selection.json()["replayed"] is True

    validated = context.client.post(
        f"/api/whatsapp/broadcasts/{broadcast_id}/validate",
        json={"expected_version": version},
    )
    assert validated.status_code == 200
    assert validated.json()["valid"] is True
    token = validated.json()["validation_token"]
    assert token is not None

    confirm_command = uuid4()
    confirm_payload = {
        "command_id": str(confirm_command),
        "expected_version": version,
        "validation_token": token,
    }
    confirmed = context.client.post(
        f"/api/whatsapp/broadcasts/{broadcast_id}/confirm",
        json=confirm_payload,
    )
    replayed_confirm = context.client.post(
        f"/api/whatsapp/broadcasts/{broadcast_id}/confirm",
        json=confirm_payload,
    )
    assert confirmed.json()["status"] == "CONFIRMED"
    assert replayed_confirm.json()["status"] == "CONFIRMED"

    immutable = context.client.put(
        f"/api/whatsapp/broadcasts/{broadcast_id}/recipients",
        json={
            "command_id": str(uuid4()),
            "customer_ids": [customer_id],
            "expected_version": version,
        },
    )
    assert immutable.status_code == 409

    start_command = uuid4()
    start_payload = {"command_id": str(start_command)}
    started = context.client.post(
        f"/api/whatsapp/broadcasts/{broadcast_id}/start", json=start_payload
    )
    replayed_start = context.client.post(
        f"/api/whatsapp/broadcasts/{broadcast_id}/start", json=start_payload
    )
    assert started.json()["status"] == "PROCESSING"
    assert replayed_start.json()["status"] == "PROCESSING"
    assert context.provider.requests == []

    process_command = uuid4()
    process_payload = {"command_id": str(process_command)}
    processed = context.client.post(
        f"/api/whatsapp/broadcasts/{broadcast_id}/process", json=process_payload
    )
    replayed_process = context.client.post(
        f"/api/whatsapp/broadcasts/{broadcast_id}/process", json=process_payload
    )
    assert processed.status_code == 200
    assert processed.json()["claimed_count"] == 1
    assert processed.json()["completed_count"] == 1
    assert replayed_process.json()["replayed"] is True
    assert len(context.provider.requests) == 1
    request = context.provider.requests[0]
    assert isinstance(request, SendTemplateRequest)
    assert request.recipient.phone == "+541161000001"
    assert [(item.name, item.value) for item in request.parameters] == [
        ("fecha", "31/08")
    ]

    messages = tuple(
        db_session.scalars(
            select(WhatsAppMessage).where(
                WhatsAppMessage.origin == WhatsAppMessageOrigin.BROADCAST
            )
        )
    )
    assert len(messages) == 1
    message = messages[0]
    assert message.broadcast_recipient_id is not None
    assert message.template_name == "oferta_asfalto"
    db_session.refresh(conversation)
    assert conversation.waiting_for_response is True
    assert db_session.scalar(select(func.count(Opportunity.id))) == opportunities_before
    db_session.commit()

    delivered = context.client.post(
        f"/api/whatsapp/dev/messages/{message.id}/statuses",
        json={
            "events": [
                {
                    "state": "DELIVERED",
                    "occurred_at": (context.now + timedelta(seconds=1)).isoformat(),
                },
                {
                    "state": "READ",
                    "occurred_at": (context.now + timedelta(seconds=2)).isoformat(),
                },
            ],
            "duplicate": True,
        },
    )
    assert delivered.status_code == 200
    db_session.expunge_all()

    detail = context.client.get(f"/api/whatsapp/broadcasts/{broadcast_id}")
    assert detail.status_code == 200
    assert detail.json()["recipients"][0]["status"] == "READ"
    assert {item["event_type"] for item in detail.json()["audit_events"]} >= {
        "CREATED",
        "RECIPIENTS_REPLACED",
        "VALIDATED",
        "CONFIRMED",
        "STARTED",
        "PROCESSED",
        "COMPLETED",
    }
    assert "storage_key" not in detail.text
    assert "provider_payload" not in detail.text

    summary = context.client.get(
        f"/api/whatsapp/broadcasts/{broadcast_id}/delivery-summary"
    )
    assert summary.status_code == 200
    assert summary.json()["message_attempt_count"] == 1
    assert summary.json()["states"] == [{"status": "READ", "count": 1}]
    assert summary.json()["read_at"] is not None
    assert summary.json()["first_completed_at"] is not None

    listed = context.client.get(
        "/api/whatsapp/broadcasts", params={"status": "COMPLETED", "limit": 1}
    )
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == broadcast_id
    assert context.client.get("/api/whatsapp/broadcasts?cursor=bad").status_code == 422
    assert (
        context.client.get(
            "/api/whatsapp/marketing-consent-events",
            params={"customer_id": customer_id, "limit": 1},
        ).status_code
        == 200
    )


def test_consent_sources_opt_out_and_append_only_enforcement(
    broadcast_context: BroadcastContext,
    db_session: Session,
) -> None:
    context = broadcast_context
    customer = _customer(db_session, "Consentido", "+54 11 6200-0001")
    customer_id = customer.id
    occurred_at = context.now - timedelta(days=1)

    missing_evidence = context.client.post(
        "/api/whatsapp/marketing-consent-events",
        json={
            "client_event_id": str(uuid4()),
            "customer_id": customer_id,
            "decision": "OPT_IN",
            "source": "EXTERNAL_FAA",
            "occurred_at": occurred_at.isoformat(),
            "effective_at": occurred_at.isoformat(),
        },
    )
    future = context.client.post(
        "/api/whatsapp/marketing-consent-events",
        json={
            "client_event_id": str(uuid4()),
            "customer_id": customer_id,
            "decision": "OPT_IN",
            "source": "EXTERNAL_FAA",
            "occurred_at": occurred_at.isoformat(),
            "effective_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "evidence_reference": "FAA-form-88",
        },
    )
    direct_effective = context.client.post(
        "/api/whatsapp/marketing-consent-events",
        json={
            "client_event_id": str(uuid4()),
            "customer_id": customer_id,
            "decision": "OPT_IN",
            "source": "FAA_CRM",
            "occurred_at": occurred_at.isoformat(),
            "effective_at": occurred_at.isoformat(),
        },
    )
    assert (missing_evidence.status_code, future.status_code) == (422, 422)
    assert direct_effective.status_code == 422

    external_id = uuid4()
    imported_payload = {
        "client_event_id": str(external_id),
        "customer_id": customer_id,
        "decision": "OPT_IN",
        "source": "EXTERNAL_FAA",
        "occurred_at": occurred_at.isoformat(),
        "effective_at": occurred_at.isoformat(),
        "evidence_reference": " FAA-form-88 ",
    }
    imported = context.client.post(
        "/api/whatsapp/marketing-consent-events", json=imported_payload
    )
    assert imported.status_code == 201
    assert imported.json()["event"]["evidence_reference"] == "FAA-form-88"

    conflict = context.client.post(
        "/api/whatsapp/marketing-consent-events",
        json={**imported_payload, "decision": "OPT_OUT"},
    )
    assert conflict.status_code == 409

    opted_out = _consent(
        context,
        customer_id,
        WhatsAppConsentDecision.OPT_OUT,
        occurred_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    assert opted_out.current.decision is WhatsAppConsentDecision.OPT_OUT
    history = context.client.get(
        "/api/whatsapp/marketing-consent-events",
        params={"customer_id": customer_id},
    )
    assert history.status_code == 200
    assert [item["decision"] for item in history.json()["items"]] == [
        "OPT_OUT",
        "OPT_IN",
    ]

    event_id = imported.json()["event"]["id"]
    with pytest.raises(DBAPIError):
        db_session.execute(
            update(WhatsAppMarketingConsentEvent)
            .where(WhatsAppMarketingConsentEvent.id == event_id)
            .values(evidence_reference="changed")
        )
        db_session.commit()
    db_session.rollback()
    with pytest.raises(DBAPIError):
        db_session.execute(
            delete(WhatsAppMarketingConsentEvent).where(
                WhatsAppMarketingConsentEvent.id == event_id
            )
        )
        db_session.commit()
    db_session.rollback()


def test_confirmation_revalidates_and_opt_out_blocks_confirmed_dispatch(
    broadcast_context: BroadcastContext,
    db_session: Session,
) -> None:
    context = broadcast_context
    first = _customer(db_session, "Primero", "+54 11 6300-0001")
    duplicate = _customer(db_session, "Duplicado", "+54 (11) 6300-0001")
    without_phone = _customer(db_session, "Sin teléfono", None)
    deleted = _customer(db_session, "Borrado", "+54 11 6300-0004")
    deleted.deleted_at = datetime.now(UTC)
    db_session.commit()
    first_id = first.id
    duplicate_id = duplicate.id
    without_phone_id = without_phone.id
    deleted_id = deleted.id
    _consent(context, first_id, WhatsAppConsentDecision.OPT_IN)

    created = _create_broadcast(context)
    broadcast_id = created.id
    selected = context.client.put(
        f"/api/whatsapp/broadcasts/{broadcast_id}/recipients",
        json={
            "command_id": str(uuid4()),
            "customer_ids": [
                first_id,
                duplicate_id,
                without_phone_id,
                deleted_id,
            ],
            "expected_version": 1,
        },
    )
    assert selected.json()["selected_count"] == 1
    assert selected.json()["duplicate_customer_ids"] == [duplicate_id]
    assert selected.json()["missing_phone_customer_ids"] == [without_phone_id]
    assert selected.json()["invalid_customer_ids"] == [deleted_id]
    version = selected.json()["version"]

    validated = context.client.post(
        f"/api/whatsapp/broadcasts/{broadcast_id}/validate",
        json={"expected_version": version},
    ).json()
    assert validated["valid"] is True
    _consent(context, first_id, WhatsAppConsentDecision.OPT_OUT)
    stale_confirm = context.client.post(
        f"/api/whatsapp/broadcasts/{broadcast_id}/confirm",
        json={
            "command_id": str(uuid4()),
            "expected_version": version,
            "validation_token": validated["validation_token"],
        },
    )
    assert stale_confirm.status_code == 409
    assert context.provider.requests == []

    _consent(context, first_id, WhatsAppConsentDecision.OPT_IN)
    validated_again = BroadcastValidationResponse.model_validate(
        context.client.post(
            f"/api/whatsapp/broadcasts/{broadcast_id}/validate",
            json={"expected_version": version},
        ).json()
    )
    assert validated_again.valid is True
    _confirm_and_start(context, broadcast_id, version, validated_again)
    _consent(context, first_id, WhatsAppConsentDecision.OPT_OUT)
    processed = context.client.post(
        f"/api/whatsapp/broadcasts/{broadcast_id}/process",
        json={"command_id": str(uuid4())},
    )
    assert processed.status_code == 200
    assert context.provider.requests == []
    detail = context.client.get(f"/api/whatsapp/broadcasts/{broadcast_id}").json()
    assert detail["status"] == "COMPLETED"
    assert detail["recipients"][0]["status"] == "BLOCKED"
    assert detail["recipients"][0]["reason_code"] == "CONSENT_OR_PHONE_CHANGED"
    summary = context.client.get(
        f"/api/whatsapp/broadcasts/{broadcast_id}/delivery-summary"
    ).json()
    assert summary["reasons"] == [{"reason": "CONSENT_OR_PHONE_CHANGED", "count": 1}]


def test_failed_retry_creates_linked_message_and_unknown_is_rejected(
    broadcast_context: BroadcastContext,
    db_session: Session,
) -> None:
    context = broadcast_context
    customer = _customer(db_session, "Retry", "+54 11 6400-0001")
    _consent(context, customer.id, WhatsAppConsentDecision.OPT_IN)
    broadcast_id, recipient_id = _ready_broadcast(context, customer.id)
    process = context.client.post(
        f"/api/whatsapp/broadcasts/{broadcast_id}/process",
        json={"command_id": str(uuid4())},
    )
    assert process.status_code == 200
    original = db_session.scalar(
        select(WhatsAppMessage).where(
            WhatsAppMessage.broadcast_recipient_id == recipient_id
        )
    )
    assert original is not None
    db_session.commit()

    failed = context.client.post(
        f"/api/whatsapp/dev/messages/{original.id}/statuses",
        json={
            "events": [
                {
                    "state": "FAILED",
                    "occurred_at": (context.now + timedelta(seconds=5)).isoformat(),
                    "error_code": "131047",
                    "error_message": "Safe provider failure",
                }
            ]
        },
    )
    assert failed.status_code == 200
    db_session.expunge_all()

    retry_command = uuid4()
    retry_payload = {
        "command_id": str(retry_command),
        "recipient_ids": [recipient_id],
    }
    retried = context.client.post(
        f"/api/whatsapp/broadcasts/{broadcast_id}/retries", json=retry_payload
    )
    replayed = context.client.post(
        f"/api/whatsapp/broadcasts/{broadcast_id}/retries", json=retry_payload
    )
    assert retried.status_code == 200
    assert len(retried.json()["created_message_ids"]) == 1
    assert replayed.json()["replayed"] is True
    retry_message = db_session.get(
        WhatsAppMessage, retried.json()["created_message_ids"][0]
    )
    assert retry_message is not None
    assert retry_message.retry_of_message_id == original.id
    assert retry_message.client_generated_id != original.client_generated_id
    assert retry_message.dispatch_state is WhatsAppDispatchState.PENDING
    assert retry_message.client_generated_id is not None
    context.provider.configure_error(
        retry_message.client_generated_id,
        ProviderErrorKind.PERMANENT_FAILURE,
        code="PERMANENT",
        safe_message="Permanent provider failure",
    )
    db_session.commit()

    second_process = context.client.post(
        f"/api/whatsapp/broadcasts/{broadcast_id}/process",
        json={"command_id": str(uuid4())},
    )
    assert second_process.status_code == 200
    assert len(context.provider.requests) == 2

    recipient = db_session.get(WhatsAppBroadcastRecipient, recipient_id)
    assert recipient is not None
    persisted_retry = db_session.scalar(
        select(WhatsAppMessage).where(WhatsAppMessage.id == retry_message.id)
    )
    assert persisted_retry is not None
    db_session.refresh(persisted_retry)
    assert persisted_retry.dispatch_state is WhatsAppDispatchState.DEFINITIVE_FAILED
    assert persisted_retry.failed_at is not None
    assert recipient.status is WhatsAppBroadcastRecipientStatus.FAILED
    recipient.status = WhatsAppBroadcastRecipientStatus.UNKNOWN
    persisted_retry.dispatch_state = WhatsAppDispatchState.UNKNOWN
    db_session.commit()
    rejected = context.client.post(
        f"/api/whatsapp/broadcasts/{broadcast_id}/retries",
        json={"command_id": str(uuid4()), "recipient_ids": [recipient_id]},
    )
    assert rejected.status_code == 200
    assert rejected.json()["created_message_ids"] == []
    assert rejected.json()["rejected_recipient_ids"] == [recipient_id]
    assert len(context.provider.requests) == 2


def test_broadcast_contracts_are_strict_authenticated_and_global(
    broadcast_context: BroadcastContext,
    db_session: Session,
) -> None:
    context = broadcast_context
    authorization = context.client.headers.pop("Authorization")
    try:
        assert context.client.get("/api/whatsapp/broadcasts").status_code == 401
        assert (
            context.client.get("/api/whatsapp/broadcast-templates").status_code == 401
        )
        assert (
            context.client.get(
                "/api/whatsapp/marketing-consent-events",
                params={"customer_id": 1},
            ).status_code
            == 401
        )
    finally:
        context.client.headers["Authorization"] = authorization

    strict = context.client.post(
        "/api/whatsapp/broadcasts",
        json={
            "client_generated_id": str(uuid4()),
            "label": "Strict",
            "template_external_id": "marketing-1",
            "parameters": [{"name": "fecha", "value": "hoy"}],
            "campaign_body": "CRM no crea contenido",
        },
    )
    assert strict.status_code == 422

    broadcast = _create_broadcast(context)
    seller = User(
        full_name="Vendedor Broadcast",
        email="vendedor-broadcast@faa.test",
        password_hash=hash_password("unused-password"),
        role=UserRole.VENDEDOR,
    )
    db_session.add(seller)
    db_session.commit()
    seller_headers = {"Authorization": f"Bearer {create_access_token(seller.id)}"}
    assert (
        context.client.get(
            f"/api/whatsapp/broadcasts/{broadcast.id}", headers=seller_headers
        ).status_code
        == 200
    )
    assert (
        context.client.post(
            "/api/whatsapp/broadcasts",
            json={
                "client_generated_id": str(uuid4()),
                "label": "Vendedor ejecuta",
                "template_external_id": "marketing-1",
                "parameters": [{"name": "fecha", "value": "mañana"}],
            },
            headers=seller_headers,
        ).status_code
        == 201
    )
    assert context.client.get("/api/whatsapp/broadcasts/999999").status_code == 404


def test_image_header_template_reuses_durable_media(
    broadcast_context: BroadcastContext,
    db_session: Session,
) -> None:
    context = broadcast_context
    image_template = ProviderTemplateSnapshot(
        external_id="marketing-image",
        name="oferta_imagen",
        language="es_AR",
        category="MARKETING",
        status="APPROVED",
        header_type=TemplateHeaderType.IMAGE,
        header_media_required=True,
    )
    context.provider.set_templates((image_template,))
    media_ref = uuid4()
    stored = context.storage.put(
        MediaPutRequest(
            media_ref=media_ref,
            content=b"fake-image",
            media_type=WhatsAppMessageType.IMAGE,
            mime_type="image/jpeg",
            filename="cabecera.jpg",
        )
    )
    customer = _customer(db_session, "Imagen", "+54 11 6500-0001")
    _consent(context, customer.id, WhatsAppConsentDecision.OPT_IN)
    created = context.client.post(
        "/api/whatsapp/broadcasts",
        json={
            "client_generated_id": str(uuid4()),
            "label": "Con imagen",
            "template_external_id": image_template.external_id,
            "parameters": [],
            "header_media_ref": str(media_ref),
        },
    )
    assert created.status_code == 201
    broadcast_id, _ = _select_validate_confirm_start(
        context, created.json()["id"], customer.id
    )
    processed = context.client.post(
        f"/api/whatsapp/broadcasts/{broadcast_id}/process",
        json={"command_id": str(uuid4())},
    )
    assert processed.status_code == 200
    request = context.provider.requests[0]
    assert isinstance(request, SendTemplateRequest)
    assert request.header_media is not None
    assert request.header_media.storage_key == stored.storage_key
    response = context.client.get(f"/api/whatsapp/broadcasts/{broadcast_id}")
    assert stored.storage_key not in response.text


def test_stale_claims_are_safely_reclaimed_or_marked_unknown(
    broadcast_context: BroadcastContext,
    db_session: Session,
) -> None:
    context = broadcast_context
    customer = _customer(db_session, "Stale", "+54 11 6600-0001")
    customer_id = customer.id
    _consent(context, customer_id, WhatsAppConsentDecision.OPT_IN)
    broadcast_id, recipient_id = _ready_broadcast(context, customer_id)

    recipient = db_session.get(WhatsAppBroadcastRecipient, recipient_id)
    assert recipient is not None
    recipient.status = WhatsAppBroadcastRecipientStatus.IN_PROGRESS
    recipient.claimed_at = datetime.now(UTC) - timedelta(hours=1)
    recipient.claim_token = uuid4()
    db_session.commit()

    reclaimed = context.client.post(
        f"/api/whatsapp/broadcasts/{broadcast_id}/process",
        json={"command_id": str(uuid4())},
    )
    assert reclaimed.status_code == 200
    assert reclaimed.json()["claimed_count"] == 1
    assert len(context.provider.requests) == 1

    message = db_session.scalar(
        select(WhatsAppMessage).where(
            WhatsAppMessage.broadcast_recipient_id == recipient_id
        )
    )
    broadcast = db_session.get(WhatsAppBroadcast, broadcast_id)
    assert message is not None
    assert broadcast is not None
    recipient.status = WhatsAppBroadcastRecipientStatus.IN_PROGRESS
    recipient.claimed_at = datetime.now(UTC) - timedelta(hours=1)
    message.dispatch_state = WhatsAppDispatchState.IN_PROGRESS
    message.external_message_id = None
    message.provider_state = None
    message.provider_status_at = None
    message.accepted_at = None
    message.sent_at = None
    broadcast.status = WhatsAppBroadcastStatus.PROCESSING
    db_session.commit()

    ambiguous = context.client.post(
        f"/api/whatsapp/broadcasts/{broadcast_id}/process",
        json={"command_id": str(uuid4())},
    )
    assert ambiguous.status_code == 200
    assert ambiguous.json()["claimed_count"] == 0
    assert len(context.provider.requests) == 1
    detail = context.client.get(f"/api/whatsapp/broadcasts/{broadcast_id}").json()
    assert detail["recipients"][0]["status"] == "UNKNOWN"
    stale_reasons = {
        event["reason_code"]
        for event in detail["audit_events"]
        if event["event_type"] == "STALE_CLAIM_RECOVERED"
    }
    assert stale_reasons == {"SAFE_RECLAIM", "MARKED_UNKNOWN"}


def _customer(
    session: Session,
    name: str,
    phone: str | None,
) -> Customer:
    customer = Customer(name=name, phone=phone)
    session.add(customer)
    session.commit()
    return customer


def _consent(
    context: BroadcastContext,
    customer_id: int,
    decision: WhatsAppConsentDecision,
    *,
    occurred_at: datetime | None = None,
) -> ConsentEventResultResponse:
    response = context.client.post(
        "/api/whatsapp/marketing-consent-events",
        json={
            "client_event_id": str(uuid4()),
            "customer_id": customer_id,
            "decision": decision.value,
            "source": WhatsAppConsentSource.FAA_CRM.value,
            "occurred_at": (
                occurred_at or datetime.now(UTC) - timedelta(seconds=1)
            ).isoformat(),
        },
    )
    assert response.status_code == 201
    return ConsentEventResultResponse.model_validate(response.json())


def _create_broadcast(context: BroadcastContext) -> BroadcastResponse:
    response = context.client.post(
        "/api/whatsapp/broadcasts",
        json={
            "client_generated_id": str(uuid4()),
            "label": "Broadcast de prueba",
            "template_external_id": "marketing-1",
            "parameters": [{"name": "fecha", "value": "31/08"}],
        },
    )
    assert response.status_code == 201
    return BroadcastResponse.model_validate(response.json())


def _ready_broadcast(
    context: BroadcastContext,
    customer_id: int,
) -> tuple[int, int]:
    created = _create_broadcast(context)
    return _select_validate_confirm_start(context, created.id, customer_id)


def _select_validate_confirm_start(
    context: BroadcastContext,
    broadcast_id: int,
    customer_id: int,
) -> tuple[int, int]:
    selected = context.client.put(
        f"/api/whatsapp/broadcasts/{broadcast_id}/recipients",
        json={
            "command_id": str(uuid4()),
            "customer_ids": [customer_id],
            "expected_version": 1,
        },
    ).json()
    validated = BroadcastValidationResponse.model_validate(
        context.client.post(
            f"/api/whatsapp/broadcasts/{broadcast_id}/validate",
            json={"expected_version": selected["version"]},
        ).json()
    )
    _confirm_and_start(context, broadcast_id, selected["version"], validated)
    detail = context.client.get(f"/api/whatsapp/broadcasts/{broadcast_id}").json()
    return broadcast_id, int(detail["recipients"][0]["id"])


def _confirm_and_start(
    context: BroadcastContext,
    broadcast_id: int,
    version: int,
    validation: BroadcastValidationResponse,
) -> None:
    confirmed = context.client.post(
        f"/api/whatsapp/broadcasts/{broadcast_id}/confirm",
        json={
            "command_id": str(uuid4()),
            "expected_version": version,
            "validation_token": str(validation.validation_token),
        },
    )
    assert confirmed.status_code == 200
    started = context.client.post(
        f"/api/whatsapp/broadcasts/{broadcast_id}/start",
        json={"command_id": str(uuid4())},
    )
    assert started.status_code == 200
    assert started.json()["status"] == WhatsAppBroadcastStatus.PROCESSING.value
