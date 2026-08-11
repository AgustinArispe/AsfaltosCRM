from __future__ import annotations

from base64 import b64encode
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from time import perf_counter
from uuid import uuid4

import pytest

from app.models import WhatsAppMessageType
from app.whatsapp import (
    FakeMediaStorage,
    MediaPutRequest,
    MetaCloudApiProvider,
    MetaConfig,
    MetaGraphClient,
    MetaHttpRequest,
    MetaHttpResponse,
    MetaTemplateSnapshotCache,
    MetaTransportError,
    ProviderErrorKind,
    ProviderMediaReference,
    ProviderRecipient,
    SendDocumentRequest,
    SendImageRequest,
    SendTemplateRequest,
    SendTextRequest,
    TemplateHeaderType,
    TemplateParameter,
    TransmissionState,
    WhatsAppProvider,
    WhatsAppProviderError,
    WindowEvaluationContext,
)
from app.whatsapp.meta_observability import (
    MetaHttpOutcome,
    MetaOperation,
    MetaWebhookEventKind,
    MetaWebhookOutcome,
)
from app.whatsapp.runtime import build_meta_whatsapp_runtime

_NOW = datetime(2026, 8, 10, 15, 0, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class _HttpObservation:
    operation: MetaOperation
    status_class: str
    outcome: MetaHttpOutcome
    duration_seconds: float


class _RecordingMetrics:
    def __init__(self) -> None:
        self.http: list[_HttpObservation] = []
        self.retries: list[tuple[MetaOperation, str]] = []
        self.transport_failures: list[tuple[MetaOperation, str]] = []
        self.rate_limits: list[MetaOperation] = []
        self.mapping_failures: list[str] = []
        self.webhook_events: list[tuple[MetaWebhookEventKind, MetaWebhookOutcome]] = []
        self.template_sync: list[str] = []

    def observe_http(
        self,
        operation: MetaOperation,
        status_class: str,
        outcome: MetaHttpOutcome,
        duration_seconds: float,
    ) -> None:
        self.http.append(
            _HttpObservation(operation, status_class, outcome, duration_seconds)
        )

    def increment_retry(self, operation: MetaOperation, reason: str) -> None:
        self.retries.append((operation, reason))

    def increment_transport_failure(
        self,
        operation: MetaOperation,
        failure_kind: str,
    ) -> None:
        self.transport_failures.append((operation, failure_kind))

    def increment_rate_limited(self, operation: MetaOperation) -> None:
        self.rate_limits.append(operation)

    def increment_mapping_failure(self, payload_kind: str) -> None:
        self.mapping_failures.append(payload_kind)

    def increment_webhook_event(
        self,
        event_kind: MetaWebhookEventKind,
        outcome: MetaWebhookOutcome,
    ) -> None:
        self.webhook_events.append((event_kind, outcome))

    def increment_template_sync(self, outcome: str) -> None:
        self.template_sync.append(outcome)


_TransportOutcome = MetaHttpResponse | MetaTransportError


class _ScriptedTransport:
    def __init__(self, outcomes: list[_TransportOutcome]) -> None:
        self._outcomes = outcomes
        self.requests: list[MetaHttpRequest] = []

    def execute(self, request: MetaHttpRequest) -> MetaHttpResponse:
        self.requests.append(request)
        if not self._outcomes:
            raise AssertionError("No scripted Meta response remains")
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, MetaTransportError):
            raise outcome
        return outcome


def _response(status_code: int, body: bytes) -> MetaHttpResponse:
    return MetaHttpResponse(
        status_code=status_code,
        headers=(("Content-Type", "application/json"),),
        body=body,
    )


def _config(*, attempts: int = 3) -> MetaConfig:
    return MetaConfig(
        graph_api_version="v26.0",
        access_token="test-access-token",
        phone_number_id="106540352242922",
        waba_id="102290129340398",
        webhook_verify_token="test-verify-token",
        app_secret="test-app-secret",
        request_timeout_seconds=10,
        retry_max_attempts=attempts,
        retry_base_seconds=0.01,
        retry_max_seconds=0.02,
    )


def _provider(
    outcomes: list[_TransportOutcome],
    *,
    attempts: int = 3,
    storage: FakeMediaStorage | None = None,
    cache: MetaTemplateSnapshotCache | None = None,
) -> tuple[
    MetaCloudApiProvider,
    _ScriptedTransport,
    _RecordingMetrics,
    MetaTemplateSnapshotCache,
]:
    config = _config(attempts=attempts)
    transport = _ScriptedTransport(outcomes)
    metrics = _RecordingMetrics()
    sleeps: list[float] = []
    graph = MetaGraphClient(
        config,
        transport,
        metrics,
        sleeper=sleeps.append,
        timer=lambda: 1.0,
    )
    selected_cache = cache or MetaTemplateSnapshotCache()
    provider = MetaCloudApiProvider(
        config,
        graph,
        storage or FakeMediaStorage(),
        metrics,
        image_max_bytes=1024,
        document_max_bytes=2048,
        now=lambda: _NOW,
        template_cache=selected_cache,
    )
    protocol_provider: WhatsAppProvider = provider
    assert protocol_provider is provider
    return provider, transport, metrics, selected_cache


def test_configuration_is_required_only_for_meta_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    names = (
        "META_GRAPH_API_VERSION",
        "META_ACCESS_TOKEN",
        "META_PHONE_NUMBER_ID",
        "META_WABA_ID",
        "META_WEBHOOK_VERIFY_TOKEN",
        "META_APP_SECRET",
    )
    for name in names:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(RuntimeError, match="META_GRAPH_API_VERSION"):
        MetaConfig.from_environment()

    values = {
        "META_GRAPH_API_VERSION": "v26.0",
        "META_ACCESS_TOKEN": "secret-token",
        "META_PHONE_NUMBER_ID": "12345",
        "META_WABA_ID": "98765",
        "META_WEBHOOK_VERIFY_TOKEN": "verify",
        "META_APP_SECRET": "secret",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    configured = MetaConfig.from_environment()
    assert configured.graph_api_version == "v26.0"
    assert "secret-token" not in repr(configured)
    assert "secret" not in repr(configured)

    monkeypatch.setenv("META_PHONE_NUMBER_ID", "not-numeric")
    with pytest.raises(RuntimeError, match="PHONE_NUMBER_ID"):
        MetaConfig.from_environment()


@pytest.mark.parametrize(
    ("config", "message"),
    [
        (replace(_config(), graph_api_version="26.0"), "API_VERSION"),
        (replace(_config(), waba_id="waba"), "WABA_ID"),
        (replace(_config(), request_timeout_seconds=0.5), "TIMEOUT"),
        (replace(_config(), retry_max_attempts=0), "MAX_ATTEMPTS"),
        (replace(_config(), retry_base_seconds=0), "BASE_SECONDS"),
        (replace(_config(), retry_max_seconds=0.001), "MAX_SECONDS"),
    ],
)
def test_meta_configuration_rejects_invalid_runtime_bounds(
    config: MetaConfig,
    message: str,
) -> None:
    with pytest.raises(RuntimeError, match=message):
        config.validate()


def test_meta_configuration_rejects_non_numeric_retry_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = {
        "META_GRAPH_API_VERSION": "v26.0",
        "META_ACCESS_TOKEN": "token",
        "META_PHONE_NUMBER_ID": "123",
        "META_WABA_ID": "456",
        "META_WEBHOOK_VERIFY_TOKEN": "verify",
        "META_APP_SECRET": "secret",
    }
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("META_REQUEST_TIMEOUT_SECONDS", "invalid")
    with pytest.raises(RuntimeError, match="must be numeric"):
        MetaConfig.from_environment()
    monkeypatch.setenv("META_REQUEST_TIMEOUT_SECONDS", "10")
    monkeypatch.setenv("META_RETRY_MAX_ATTEMPTS", "invalid")
    with pytest.raises(RuntimeError, match="must be an integer"):
        MetaConfig.from_environment()


def test_meta_runtime_assembles_provider_and_webhook_without_network() -> None:
    runtime = build_meta_whatsapp_runtime(
        config=_config(),
        storage=FakeMediaStorage(),
    )
    assert isinstance(runtime.provider, MetaCloudApiProvider)
    assert runtime.webhook is not None


def test_text_image_and_document_requests_use_versioned_graph_contracts() -> None:
    storage = FakeMediaStorage()
    stored = storage.put(
        MediaPutRequest(
            media_ref=uuid4(),
            content=b"%PDF-1.7 test",
            media_type=WhatsAppMessageType.DOCUMENT,
            mime_type="application/pdf",
            filename="ficha.pdf",
        )
    )
    provider, transport, metrics, _ = _provider(
        [
            _response(200, b'{"messages":[{"id":"wamid.text"}]}'),
            _response(200, b'{"messages":[{"id":"wamid.image"}]}'),
            _response(200, b'{"id":"media-uploaded"}'),
            _response(200, b'{"messages":[{"id":"wamid.document"}]}'),
        ],
        storage=storage,
    )
    recipient = ProviderRecipient(phone="+54 (11) 5555-1234")
    text = provider.send_text(SendTextRequest(recipient, uuid4(), "Hola"))
    image = provider.send_image(
        SendImageRequest(
            recipient,
            uuid4(),
            ProviderMediaReference("existing-image", None, "image/jpeg", None),
            "Obra",
        )
    )
    upload_started = perf_counter()
    document = provider.send_document(
        SendDocumentRequest(
            recipient,
            uuid4(),
            ProviderMediaReference(
                None,
                stored.storage_key,
                "application/pdf",
                "ficha.pdf",
            ),
            None,
        )
    )
    assert perf_counter() - upload_started < 10.0

    assert (text.external_message_id, image.external_message_id) == (
        "wamid.text",
        "wamid.image",
    )
    assert document.external_message_id == "wamid.document"
    assert text.initial_state is None
    assert all(
        request.url.startswith("https://graph.facebook.com/v26.0/")
        for request in transport.requests
    )
    assert all(
        ("Authorization", "Bearer test-access-token") in request.headers
        for request in transport.requests
    )
    assert b'"to":"541155551234"' in _body(transport.requests[0])
    assert b'"id":"existing-image"' in _body(transport.requests[1])
    assert b'name="messaging_product"' in _body(transport.requests[2])
    assert b"%PDF-1.7 test" in _body(transport.requests[2])
    assert metrics.http[-1].outcome is MetaHttpOutcome.SUCCESS


def test_provider_maps_explicit_and_transport_failures_without_secret_leakage() -> None:
    recipient = ProviderRecipient(phone="541155551234")
    request = SendTextRequest(recipient, uuid4(), "sensitive body")

    permanent, _, _, _ = _provider(
        [_response(400, b'{"error":{"message":"raw secret","code":131047}}')]
    )
    with pytest.raises(WhatsAppProviderError) as permanent_error:
        permanent.send_text(request)
    assert permanent_error.value.details.kind is ProviderErrorKind.PERMANENT_FAILURE
    assert permanent_error.value.details.code == "131047"
    assert "raw secret" not in str(permanent_error.value)

    retryable, transport, metrics, _ = _provider(
        [
            _response(400, b'{"error":{"code":130429}}'),
            _response(500, b"{}"),
            _response(503, b"{}"),
        ]
    )
    with pytest.raises(WhatsAppProviderError) as retryable_error:
        retryable.send_text(request)
    assert retryable_error.value.details.kind is ProviderErrorKind.RETRYABLE_FAILURE
    assert len(transport.requests) == 3
    assert len(metrics.retries) == 2
    assert metrics.rate_limits == [MetaOperation.SEND_TEXT]

    before, before_transport, _, _ = _provider(
        [
            MetaTransportError(TransmissionState.BEFORE),
            MetaTransportError(TransmissionState.BEFORE),
        ],
        attempts=2,
    )
    with pytest.raises(WhatsAppProviderError) as before_error:
        before.send_text(request)
    assert (
        before_error.value.details.kind is ProviderErrorKind.TIMEOUT_BEFORE_ACCEPTANCE
    )
    assert len(before_transport.requests) == 2

    unknown, unknown_transport, _, _ = _provider(
        [MetaTransportError(TransmissionState.AFTER_OR_UNKNOWN)]
    )
    with pytest.raises(WhatsAppProviderError) as unknown_error:
        unknown.send_text(request)
    assert (
        unknown_error.value.details.kind is ProviderErrorKind.TIMEOUT_UNKNOWN_ACCEPTANCE
    )
    assert unknown_error.value.details.acceptance_unknown is True
    assert len(unknown_transport.requests) == 1


def test_ambiguous_success_is_unknown_and_is_not_retried() -> None:
    provider, transport, metrics, _ = _provider([_response(200, b'{"messages":[]}')])
    with pytest.raises(WhatsAppProviderError) as error:
        provider.send_text(SendTextRequest(ProviderRecipient("5411"), uuid4(), "Hola"))
    assert error.value.details.acceptance_unknown is True
    assert len(transport.requests) == 1
    assert metrics.mapping_failures == ["send_response"]


def test_media_download_resolves_fresh_url_and_verifies_metadata() -> None:
    content = b"%PDF-1.7 downloaded"
    checksum = b64encode(sha256(content).digest()).decode()
    provider, transport, _, _ = _provider(
        [
            _response(
                200,
                (
                    '{"id":"media-1","url":"https://lookaside.fbsbx.com/media",'
                    f'"mime_type":"application/pdf","sha256":"{checksum}",'
                    f'"file_size":{len(content)}}}'
                ).encode(),
            ),
            MetaHttpResponse(
                200,
                (("Content-Type", "application/pdf"),),
                content,
            ),
        ]
    )
    download_started = perf_counter()
    payload = provider.download_media(
        ProviderMediaReference("media-1", None, "application/pdf", "ficha.pdf")
    )
    assert perf_counter() - download_started < 10.0
    assert payload.content == content
    assert payload.filename == "ficha.pdf"
    assert "lookaside.fbsbx.com" in transport.requests[1].url
    assert transport.requests[1].max_response_bytes == 2048


def test_media_download_reresolves_expired_url_and_rejects_bad_integrity() -> None:
    content = b"image-bytes"
    good_checksum = b64encode(sha256(content).digest()).decode()
    resolution = (
        '{"id":"media-2","url":"https://lookaside.fbsbx.com/media",'
        f'"mime_type":"image/jpeg","sha256":"{good_checksum}",'
        f'"file_size":{len(content)}}}'
    ).encode()
    provider, transport, _, _ = _provider(
        [
            _response(200, resolution),
            _response(404, b"expired"),
            _response(200, resolution),
            MetaHttpResponse(200, (("Content-Type", "image/jpeg"),), content),
        ]
    )
    assert (
        provider.download_media(
            ProviderMediaReference("media-2", None, "image/jpeg", None)
        ).content
        == content
    )
    assert len(transport.requests) == 4

    invalid, _, _, _ = _provider(
        [
            _response(
                200,
                b'{"id":"media-3","url":"https://evil.example/media",'
                b'"mime_type":"image/jpeg"}',
            )
        ]
    )
    with pytest.raises(WhatsAppProviderError, match="URL is invalid"):
        invalid.download_media(
            ProviderMediaReference("media-3", None, "image/jpeg", None)
        )


def test_template_sync_is_complete_atomic_and_supported_shapes_send() -> None:
    first_page = b"""{
      "data":[{"id":"1","name":"obra","language":"es_AR",
      "category":"UTILITY","status":"APPROVED","parameter_format":"NAMED",
      "components":[{"type":"BODY","text":"Hola {{name}}"}]}],
      "paging":{"cursors":{"after":"cursor-2"},"next":"opaque"}}
    """
    second_page = b"""{
      "data":[{"id":"2","name":"catalogo","language":"es_AR",
      "category":"UTILITY","status":"PAUSED","parameter_format":"NAMED",
      "components":[{"type":"HEADER","format":"IMAGE"},{"type":"BODY"}]}]
    }"""
    provider, transport, metrics, cache = _provider(
        [
            _response(200, first_page),
            _response(200, second_page),
            _response(200, b'{"messages":[{"id":"wamid.template"}]}'),
        ]
    )
    sync_started = perf_counter()
    snapshots = provider.list_templates()
    assert perf_counter() - sync_started < 15.0
    assert [(item.name, item.language, item.status) for item in snapshots] == [
        ("obra", "es_AR", "APPROVED"),
        ("catalogo", "es_AR", "PAUSED"),
    ]
    assert "after=cursor-2" in transport.requests[1].url
    sent = provider.send_template(
        SendTemplateRequest(
            ProviderRecipient("541155551234"),
            uuid4(),
            "obra",
            "es_AR",
            (TemplateParameter("name", "Santiago"),),
        )
    )
    assert sent.external_message_id == "wamid.template"
    assert b'"parameter_name":"name"' in _body(transport.requests[2])
    assert metrics.template_sync == ["success"]

    failing, _, failing_metrics, _ = _provider(
        [_response(200, first_page), _response(500, b"{}")],
        attempts=1,
        cache=cache,
    )
    with pytest.raises(WhatsAppProviderError):
        failing.list_templates()
    assert [item.external_id for item in cache.snapshots] == ["1", "2"]
    assert failing_metrics.template_sync == ["failed"]

    with pytest.raises(WhatsAppProviderError, match="unsupported"):
        provider.send_template(
            SendTemplateRequest(
                ProviderRecipient("541155551234"),
                uuid4(),
                "catalogo",
                "es_AR",
                (),
            )
        )


@pytest.mark.parametrize(
    ("header_format", "mime_type", "serialized_type"),
    (
        ("IMAGE", "image/jpeg", b'"type":"image"'),
        ("DOCUMENT", "application/pdf", b'"type":"document"'),
    ),
)
def test_supported_template_media_headers_are_serialized(
    header_format: str,
    mime_type: str,
    serialized_type: bytes,
) -> None:
    template_payload = (
        '{"data":[{"id":"media-template","name":"oferta_media",'
        '"language":"es_AR","category":"MARKETING","status":"APPROVED",'
        f'"components":[{{"type":"HEADER","format":"{header_format}"}},'
        '{"type":"BODY","text":"Oferta FAA"}]}]}'
    ).encode()
    provider, transport, _, _ = _provider(
        [
            _response(200, template_payload),
            _response(200, b'{"messages":[{"id":"wamid.media-template"}]}'),
        ]
    )
    snapshot = provider.list_templates()[0]
    assert snapshot.header_type is TemplateHeaderType(header_format)
    assert snapshot.header_media_required is True
    assert snapshot.supported_for_send is True

    sent = provider.send_template(
        SendTemplateRequest(
            recipient=ProviderRecipient("541155551234"),
            client_generated_id=uuid4(),
            template_name="oferta_media",
            language="es_AR",
            parameters=(),
            header_media=ProviderMediaReference(
                "media-header",
                None,
                mime_type,
                "header",
            ),
        )
    )
    assert sent.external_message_id == "wamid.media-template"
    message_body = _body(transport.requests[1])
    assert serialized_type in message_body
    assert b'"id":"media-header"' in message_body


def test_window_boundaries_and_fixture_performance_budgets() -> None:
    provider, _, _, _ = _provider([])
    last_inbound = _NOW - timedelta(hours=24)
    at_expiry = provider.evaluate_window(WindowEvaluationContext(last_inbound, _NOW))
    before_expiry = provider.evaluate_window(
        WindowEvaluationContext(last_inbound, _NOW - timedelta(microseconds=1))
    )
    without_inbound = provider.evaluate_window(WindowEvaluationContext(None, _NOW))
    assert at_expiry.can_send_freeform is False
    assert at_expiry.window_expires_at == _NOW
    assert before_expiry.can_send_freeform is True
    assert without_inbound.window_expires_at is None

    benchmark_provider, _, _, _ = _provider(
        [_response(200, b'{"messages":[{"id":"wamid.fast"}]}')]
    )
    started = perf_counter()
    benchmark_provider.send_text(
        SendTextRequest(ProviderRecipient("5411"), uuid4(), "benchmark")
    )
    assert perf_counter() - started < 3.0


def _body(request: MetaHttpRequest) -> bytes:
    return request.body or b""
