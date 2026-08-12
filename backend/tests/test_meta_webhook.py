from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256
from hmac import new as hmac_new
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
    Opportunity,
    User,
    WhatsAppMessage,
    WhatsAppMessageStatusEvent,
    WhatsAppProviderState,
)
from app.schemas.whatsapp import OutboundMessageResponse
from app.whatsapp import (
    FakeMediaStorage,
    MetaCloudApiProvider,
    MetaConfig,
    MetaGraphClient,
    MetaHttpRequest,
    MetaHttpResponse,
    MetaWebhookIntegration,
    MetaWebhookMapper,
    MetaWebhookVerifier,
    NullMetaMetrics,
)
from app.whatsapp.meta_observability import (
    MetaHttpOutcome,
    MetaOperation,
    MetaWebhookEventKind,
    MetaWebhookOutcome,
)
from app.whatsapp.runtime import WhatsAppRuntime, build_fake_whatsapp_runtime
from app.whatsapp.webhook_contracts import (
    ProviderIgnoredEvent,
    ProviderInboundEvent,
    ProviderStatusEvent,
    ProviderWebhookMappingError,
)
from conftest import development_security_settings

_APP_SECRET = "test-app-secret"
_VERIFY_TOKEN = "test-verify-token"
_WABA_ID = "102290129340398"
_PHONE_NUMBER_ID = "106540352242922"
_TIMESTAMP = "1786374000"


class _WebhookMetrics:
    def __init__(self) -> None:
        self.mapping_failures: list[str] = []
        self.events: list[tuple[MetaWebhookEventKind, MetaWebhookOutcome]] = []

    def observe_http(
        self,
        operation: MetaOperation,
        status_class: str,
        outcome: MetaHttpOutcome,
        duration_seconds: float,
    ) -> None:
        del operation, status_class, outcome, duration_seconds

    def increment_retry(self, operation: MetaOperation, reason: str) -> None:
        del operation, reason

    def increment_transport_failure(
        self,
        operation: MetaOperation,
        failure_kind: str,
    ) -> None:
        del operation, failure_kind

    def increment_rate_limited(self, operation: MetaOperation) -> None:
        del operation

    def increment_mapping_failure(self, payload_kind: str) -> None:
        self.mapping_failures.append(payload_kind)

    def increment_webhook_event(
        self,
        event_kind: MetaWebhookEventKind,
        outcome: MetaWebhookOutcome,
    ) -> None:
        self.events.append((event_kind, outcome))

    def increment_template_sync(self, outcome: str) -> None:
        del outcome


class _AcceptedTransport:
    def __init__(self) -> None:
        self.requests: list[MetaHttpRequest] = []

    def execute(self, request: MetaHttpRequest) -> MetaHttpResponse:
        self.requests.append(request)
        return MetaHttpResponse(
            status_code=200,
            headers=(("Content-Type", "application/json"),),
            body=b'{"messages":[{"id":"wamid.outbound.meta"}]}',
        )


def _config() -> MetaConfig:
    return MetaConfig(
        graph_api_version="v26.0",
        access_token="test-access-token",
        phone_number_id=_PHONE_NUMBER_ID,
        waba_id=_WABA_ID,
        webhook_verify_token=_VERIFY_TOKEN,
        app_secret=_APP_SECRET,
        request_timeout_seconds=10,
        retry_max_attempts=1,
        retry_base_seconds=0.01,
        retry_max_seconds=0.01,
    )


def _mapper(metrics: _WebhookMetrics | None = None) -> MetaWebhookMapper:
    return MetaWebhookMapper(
        waba_id=_WABA_ID,
        phone_number_id=_PHONE_NUMBER_ID,
        metrics=metrics or _WebhookMetrics(),
    )


def _signed_headers(body: bytes) -> dict[str, str]:
    digest = hmac_new(_APP_SECRET.encode(), body, sha256).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": f"sha256={digest}",
    }


def _envelope(contents: str) -> bytes:
    return (
        '{"object":"whatsapp_business_account","entry":[{"id":"'
        + _WABA_ID
        + '","changes":[{"field":"messages","value":'
        + contents
        + "}]}]}"
    ).encode()


def test_webhook_verification_uses_exact_raw_body_and_constant_contract() -> None:
    verifier = MetaWebhookVerifier(
        verify_token=_VERIFY_TOKEN,
        app_secret=_APP_SECRET,
    )
    assert (
        verifier.verify_challenge(
            mode="subscribe",
            verify_token=_VERIFY_TOKEN,
            challenge="challenge-value",
        )
        == "challenge-value"
    )
    assert (
        verifier.verify_challenge(
            mode="subscribe",
            verify_token="wrong",
            challenge="challenge-value",
        )
        is None
    )
    body = b'{"event":"value"}'
    signature = _signed_headers(body)["X-Hub-Signature-256"]
    assert verifier.verify_signature(body, signature) is True
    assert verifier.verify_signature(body + b" ", signature) is False
    assert verifier.verify_signature(body, None) is False
    assert verifier.verify_signature(body, "sha256=short") is False


def test_mapper_maps_text_image_document_and_statuses_in_order() -> None:
    metrics = _WebhookMetrics()
    body = _envelope(
        """{
          "messaging_product":"whatsapp",
          "metadata":{"phone_number_id":"106540352242922"},
          "contacts":[{"wa_id":"541155551234","profile":{"name":"Obras Sur"}}],
          "messages":[
            {"from":"541155551234","id":"wamid.text","timestamp":"1786374000",
             "type":"text","text":{"body":"Necesito asfalto"}},
            {"from":"541155551234","id":"wamid.image","timestamp":"1786374001",
             "type":"image","image":{"id":"media-image","mime_type":"image/jpeg",
             "caption":"Foto","url":"https://lookaside.fbsbx.com/temporary"}},
            {"from":"541155551234","id":"wamid.document","timestamp":"1786374002",
             "type":"document","document":{"id":"media-doc","mime_type":"application/pdf",
             "filename":"pedido.pdf","caption":"Pedido"}}
          ],
          "statuses":[
            {"id":"wamid.outbound","status":"read","timestamp":"1786374004"},
            {"id":"wamid.outbound","status":"delivered","timestamp":"1786374003"}
          ]
        }"""
    )
    events = _mapper(metrics).map_events(body)
    assert len(events) == 5
    assert isinstance(events[0], ProviderInboundEvent)
    assert events[0].body == "Necesito asfalto"
    assert events[0].display_name == "Obras Sur"
    assert isinstance(events[1], ProviderInboundEvent)
    assert events[1].attachment is not None
    assert events[1].attachment.provider_media_id == "media-image"
    assert not hasattr(events[1].attachment, "url")
    assert isinstance(events[2], ProviderInboundEvent)
    assert events[2].attachment is not None
    assert events[2].attachment.filename == "pedido.pdf"
    assert isinstance(events[3], ProviderStatusEvent)
    assert events[3].state is WhatsAppProviderState.READ
    assert isinstance(events[4], ProviderStatusEvent)
    assert events[4].state is WhatsAppProviderState.DELIVERED
    assert events[3].occurred_at.tzinfo is UTC
    assert metrics.mapping_failures == []


def test_mapper_ignores_unknown_events_and_rejects_malformed_recognized_data() -> None:
    metrics = _WebhookMetrics()
    ignored = _mapper(metrics).map_events(
        _envelope(
            """{"messaging_product":"whatsapp",
            "metadata":{"phone_number_id":"106540352242922"},
            "messages":[{"type":"audio","id":"wamid.audio"}],
            "statuses":[{"id":"wamid.voice","status":"played","timestamp":"1786374000"}]}"""
        )
    )
    assert all(isinstance(event, ProviderIgnoredEvent) for event in ignored)
    assert (
        metrics.events.count((MetaWebhookEventKind.UNKNOWN, MetaWebhookOutcome.IGNORED))
        == 2
    )

    malformed = _envelope(
        """{"messaging_product":"whatsapp",
        "metadata":{"phone_number_id":"106540352242922"},
        "messages":[{"from":"5411","id":"wamid.bad","timestamp":"bad",
        "type":"text","text":{"body":"Hola"}}]}"""
    )
    with pytest.raises(ProviderWebhookMappingError, match="timestamp"):
        _mapper(metrics).map_events(malformed)
    assert "message" in metrics.mapping_failures


def _meta_runtime(
    *,
    provider_now: datetime | None = None,
) -> tuple[WhatsAppRuntime, _AcceptedTransport]:
    config = _config()
    storage = FakeMediaStorage()
    metrics = NullMetaMetrics()
    transport = _AcceptedTransport()
    selected_provider_now = provider_now or datetime.fromtimestamp(
        int(_TIMESTAMP) + 60,
        tz=UTC,
    )
    graph = MetaGraphClient(
        config,
        transport,
        metrics,
        sleeper=lambda _: None,
    )
    provider = MetaCloudApiProvider(
        config,
        graph,
        storage,
        metrics,
        image_max_bytes=1024,
        document_max_bytes=2048,
        now=lambda: selected_provider_now,
    )
    webhook = MetaWebhookIntegration(
        MetaWebhookVerifier(
            verify_token=_VERIFY_TOKEN,
            app_secret=_APP_SECRET,
        ),
        MetaWebhookMapper(
            waba_id=_WABA_ID,
            phone_number_id=_PHONE_NUMBER_ID,
            metrics=metrics,
        ),
    )
    return (
        replace(
            build_fake_whatsapp_runtime(storage=storage),
            provider=provider,
            webhook=webhook,
        ),
        transport,
    )


def _client(
    db_session: Session,
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
    return TestClient(application)


def test_meta_route_table_excludes_fake_dev_and_fake_excludes_meta_webhook() -> None:
    meta_runtime, _ = _meta_runtime()
    meta_routes = TestClient(create_app(meta_runtime)).get("/openapi.json").text
    fake_routes = (
        TestClient(
            create_app(
                build_fake_whatsapp_runtime(),
                security_settings=development_security_settings(),
            )
        )
        .get("/openapi.json")
        .text
    )
    assert "/api/whatsapp/provider/webhook" in meta_routes
    assert "/api/whatsapp/dev/inbound" not in meta_routes
    assert "/api/whatsapp/provider/webhook" not in fake_routes
    assert "/api/whatsapp/dev/inbound" in fake_routes


def test_provider_webhook_api_processes_inbound_dedupe_and_out_of_order_status(
    db_session: Session,
    supervisor_user: User,
) -> None:
    test_now = datetime.now(UTC)
    test_timestamp = int(test_now.timestamp())
    runtime, transport = _meta_runtime(provider_now=test_now)
    client = _client(db_session, runtime)
    verification = client.get(
        "/api/whatsapp/provider/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": _VERIFY_TOKEN,
            "hub.challenge": "verified-challenge",
        },
    )
    assert verification.status_code == 200
    assert verification.text == "verified-challenge"

    inbound = _envelope(
        """{"messaging_product":"whatsapp",
        "metadata":{"phone_number_id":"106540352242922"},
        "contacts":[{"wa_id":"541155559999","profile":{"name":"Cliente Meta"}}],
        "messages":[{"from":"541155559999","id":"wamid.inbound.meta",
        "timestamp":"TEST_TIMESTAMP","type":"text","text":{"body":"Consulta"}}]}""".replace(
            "TEST_TIMESTAMP",
            str(test_timestamp),
        )
    )
    first = client.post(
        "/api/whatsapp/provider/webhook",
        content=inbound,
        headers=_signed_headers(inbound),
    )
    replay = client.post(
        "/api/whatsapp/provider/webhook",
        content=inbound,
        headers=_signed_headers(inbound),
    )
    assert (first.status_code, replay.status_code) == (200, 200)
    assert db_session.scalar(select(func.count(WhatsAppMessage.id))) == 1
    assert db_session.scalar(select(func.count(Customer.id))) == 1
    assert db_session.scalar(select(func.count(Opportunity.id))) == 1
    inbound_message = db_session.scalar(
        select(WhatsAppMessage).where(
            WhatsAppMessage.external_message_id == "wamid.inbound.meta"
        )
    )
    assert inbound_message is not None
    db_session.commit()

    client.headers["Authorization"] = (
        f"Bearer {create_access_token(supervisor_user.id)}"
    )
    outbound_response = client.post(
        f"/api/whatsapp/conversations/{inbound_message.conversation_id}/messages",
        json={
            "message_type": "TEXT",
            "client_generated_id": str(uuid4()),
            "body": "Respuesta FAA",
        },
    )
    assert outbound_response.status_code == 201, outbound_response.text
    outbound = OutboundMessageResponse.model_validate(outbound_response.json())
    assert outbound.message.external_message_id == "wamid.outbound.meta"
    assert len(transport.requests) == 1

    statuses = _envelope(
        """{"messaging_product":"whatsapp",
        "metadata":{"phone_number_id":"106540352242922"},
        "statuses":[
          {"id":"wamid.outbound.meta","status":"read","timestamp":"READ_TIMESTAMP"},
          {"id":"wamid.outbound.meta","status":"delivered","timestamp":"DELIVERED_TIMESTAMP"}
        ]}""".replace("READ_TIMESTAMP", str(test_timestamp + 60)).replace(
            "DELIVERED_TIMESTAMP",
            str(test_timestamp + 50),
        )
    )
    status_response = client.post(
        "/api/whatsapp/provider/webhook",
        content=statuses,
        headers=_signed_headers(statuses),
    )
    assert status_response.status_code == 200
    db_session.expire_all()
    persisted = db_session.get(WhatsAppMessage, outbound.message.id)
    assert persisted is not None
    assert persisted.provider_state is WhatsAppProviderState.READ
    assert db_session.scalar(select(func.count(WhatsAppMessageStatusEvent.id))) == 2

    invalid_signature = client.post(
        "/api/whatsapp/provider/webhook",
        content=inbound,
        headers={"X-Hub-Signature-256": "sha256=" + "0" * 64},
    )
    assert invalid_signature.status_code == 403


def test_signed_unknown_is_acknowledged_and_malformed_is_rejected(
    db_session: Session,
) -> None:
    runtime, _ = _meta_runtime()
    client = _client(db_session, runtime)
    unknown = b'{"object":"another_product","entry":[]}'
    assert (
        client.post(
            "/api/whatsapp/provider/webhook",
            content=unknown,
            headers=_signed_headers(unknown),
        ).status_code
        == 200
    )
    malformed = _envelope(
        """{"messaging_product":"whatsapp",
        "metadata":{"phone_number_id":"106540352242922"},
        "messages":[{"from":"5411","id":"wamid.bad","timestamp":"bad",
        "type":"text","text":{"body":"Hola"}}]}"""
    )
    assert (
        client.post(
            "/api/whatsapp/provider/webhook",
            content=malformed,
            headers=_signed_headers(malformed),
        ).status_code
        == 400
    )
