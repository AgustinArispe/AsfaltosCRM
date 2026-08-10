from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from http.client import HTTPResponse, HTTPSConnection
from socket import gaierror
from ssl import create_default_context
from time import monotonic, sleep
from typing import Protocol
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, ValidationError

from app.whatsapp.meta_config import MetaConfig
from app.whatsapp.meta_observability import (
    MetaHttpOutcome,
    MetaMetrics,
    MetaOperation,
)

_GRAPH_ORIGIN = "https://graph.facebook.com"
_MAX_JSON_RESPONSE_BYTES = 2_097_152
_RATE_LIMIT_ERROR_CODES = frozenset({4, 17, 32, 613, 80004, 130429, 131048, 131056})
_RETRYABLE_ERROR_CODES = _RATE_LIMIT_ERROR_CODES | {1, 2, 131000}


class TransmissionState(StrEnum):
    BEFORE = "before_transmission"
    AFTER_OR_UNKNOWN = "after_or_unknown_transmission"


@dataclass(frozen=True, slots=True)
class MetaHttpRequest:
    method: str
    url: str
    headers: tuple[tuple[str, str], ...]
    body: bytes | None
    timeout_seconds: float
    max_response_bytes: int


@dataclass(frozen=True, slots=True)
class MetaHttpResponse:
    status_code: int
    headers: tuple[tuple[str, str], ...]
    body: bytes


class MetaTransportError(Exception):
    def __init__(self, transmission_state: TransmissionState) -> None:
        self.transmission_state = transmission_state
        super().__init__("Meta transport request failed")


class MetaResponseTooLargeError(Exception):
    """Raised before an oversized provider body is returned to a mapper."""


class MetaHttpTransport(Protocol):
    def execute(self, request: MetaHttpRequest) -> MetaHttpResponse: ...


class HttpsMetaHttpTransport:
    def execute(self, request: MetaHttpRequest) -> MetaHttpResponse:
        parsed = urlsplit(request.url)
        if parsed.scheme != "https" or parsed.hostname is None:
            raise MetaTransportError(TransmissionState.BEFORE)
        connection = HTTPSConnection(
            parsed.hostname,
            port=parsed.port,
            timeout=request.timeout_seconds,
            context=create_default_context(),
        )
        try:
            try:
                connection.connect()
            except (ConnectionError, TimeoutError, gaierror) as error:
                raise MetaTransportError(TransmissionState.BEFORE) from error
            target = parsed.path or "/"
            if parsed.query:
                target = f"{target}?{parsed.query}"
            try:
                connection.request(
                    request.method,
                    target,
                    body=request.body,
                    headers=dict(request.headers),
                )
                response = connection.getresponse()
                return MetaHttpResponse(
                    status_code=response.status,
                    headers=tuple(response.getheaders()),
                    body=_read_bounded(response, request.max_response_bytes),
                )
            except MetaResponseTooLargeError:
                raise
            except (ConnectionError, TimeoutError, OSError) as error:
                raise MetaTransportError(TransmissionState.AFTER_OR_UNKNOWN) from error
        finally:
            connection.close()


def _read_bounded(response: HTTPResponse, maximum: int) -> bytes:
    content = response.read(maximum + 1)
    if len(content) > maximum:
        raise MetaResponseTooLargeError("Meta response exceeded its safe limit")
    return content


class MetaGraphErrorBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message: str | None = None
    type: str | None = None
    code: int | None = None
    error_subcode: int | None = None


class MetaGraphErrorEnvelope(BaseModel):
    model_config = ConfigDict(extra="ignore")

    error: MetaGraphErrorBody


@dataclass(frozen=True, slots=True)
class _MetaGraphErrorInfo:
    safe_code: str
    numeric_code: int | None


class MetaGraphFailureKind(StrEnum):
    PERMANENT = "permanent"
    RETRYABLE = "retryable"
    TIMEOUT_BEFORE = "timeout_before"
    ACCEPTANCE_UNKNOWN = "acceptance_unknown"


class MetaGraphFailure(Exception):
    def __init__(
        self,
        kind: MetaGraphFailureKind,
        *,
        code: str | None,
        safe_message: str,
    ) -> None:
        self.kind = kind
        self.code = code
        self.safe_message = safe_message
        super().__init__(safe_message)


class MetaGraphClient:
    def __init__(
        self,
        config: MetaConfig,
        transport: MetaHttpTransport,
        metrics: MetaMetrics,
        *,
        sleeper: Callable[[float], None] = sleep,
        timer: Callable[[], float] = monotonic,
    ) -> None:
        self._config = config
        self._transport = transport
        self._metrics = metrics
        self._sleeper = sleeper
        self._timer = timer

    def request_json(
        self,
        *,
        operation: MetaOperation,
        method: str,
        path: str,
        body: bytes | None = None,
        content_type: str = "application/json",
        message_acceptance_possible: bool = False,
    ) -> bytes:
        return self._request(
            operation=operation,
            method=method,
            url=self.graph_url(path),
            body=body,
            content_type=content_type,
            max_response_bytes=_MAX_JSON_RESPONSE_BYTES,
            message_acceptance_possible=message_acceptance_possible,
            allow_retry_after_transmission=not message_acceptance_possible,
        ).body

    def download(
        self,
        *,
        url: str,
        maximum_bytes: int,
    ) -> MetaHttpResponse:
        if not _is_allowed_media_url(url):
            raise MetaGraphFailure(
                MetaGraphFailureKind.PERMANENT,
                code="META_MEDIA_URL_INVALID",
                safe_message="Meta media URL is invalid",
            )
        return self._request(
            operation=MetaOperation.MEDIA_DOWNLOAD,
            method="GET",
            url=url,
            body=None,
            content_type=None,
            max_response_bytes=maximum_bytes,
            message_acceptance_possible=False,
            allow_retry_after_transmission=True,
        )

    def graph_url(self, path: str) -> str:
        normalized_path = path if path.startswith("/") else f"/{path}"
        return f"{_GRAPH_ORIGIN}/{self._config.graph_api_version}{normalized_path}"

    def _request(
        self,
        *,
        operation: MetaOperation,
        method: str,
        url: str,
        body: bytes | None,
        content_type: str | None,
        max_response_bytes: int,
        message_acceptance_possible: bool,
        allow_retry_after_transmission: bool,
    ) -> MetaHttpResponse:
        headers = [("Authorization", f"Bearer {self._config.access_token}")]
        if content_type is not None:
            headers.append(("Content-Type", content_type))
        for attempt in range(1, self._config.retry_max_attempts + 1):
            started = self._timer()
            try:
                response = self._transport.execute(
                    MetaHttpRequest(
                        method=method,
                        url=url,
                        headers=tuple(headers),
                        body=body,
                        timeout_seconds=self._config.request_timeout_seconds,
                        max_response_bytes=max_response_bytes,
                    )
                )
            except MetaResponseTooLargeError as error:
                self._metrics.observe_http(
                    operation,
                    "none",
                    MetaHttpOutcome.MAPPING_ERROR,
                    self._timer() - started,
                )
                raise MetaGraphFailure(
                    MetaGraphFailureKind.PERMANENT,
                    code="META_RESPONSE_TOO_LARGE",
                    safe_message="Meta response exceeded its safe limit",
                ) from error
            except MetaTransportError as error:
                self._metrics.observe_http(
                    operation,
                    "none",
                    MetaHttpOutcome.TRANSPORT_ERROR,
                    self._timer() - started,
                )
                self._metrics.increment_transport_failure(
                    operation,
                    error.transmission_state.value,
                )
                if (
                    error.transmission_state is TransmissionState.AFTER_OR_UNKNOWN
                    and message_acceptance_possible
                ):
                    raise MetaGraphFailure(
                        MetaGraphFailureKind.ACCEPTANCE_UNKNOWN,
                        code="META_ACCEPTANCE_UNKNOWN",
                        safe_message="Meta message acceptance is unknown",
                    ) from error
                if attempt < self._config.retry_max_attempts and (
                    error.transmission_state is TransmissionState.BEFORE
                    or allow_retry_after_transmission
                ):
                    self._retry(operation, attempt, error.transmission_state.value)
                    continue
                kind = (
                    MetaGraphFailureKind.TIMEOUT_BEFORE
                    if error.transmission_state is TransmissionState.BEFORE
                    else MetaGraphFailureKind.RETRYABLE
                )
                raise MetaGraphFailure(
                    kind,
                    code="META_TRANSPORT_FAILURE",
                    safe_message="Meta transport is temporarily unavailable",
                ) from error

            status_class = f"{response.status_code // 100}xx"
            if 200 <= response.status_code < 300:
                self._metrics.observe_http(
                    operation,
                    status_class,
                    MetaHttpOutcome.SUCCESS,
                    self._timer() - started,
                )
                return response
            self._metrics.observe_http(
                operation,
                status_class,
                MetaHttpOutcome.PROVIDER_ERROR,
                self._timer() - started,
            )
            error_info = _safe_graph_error(response.body, response.status_code)
            rate_limited = (
                response.status_code == 429
                or error_info.numeric_code in _RATE_LIMIT_ERROR_CODES
            )
            retryable = (
                response.status_code in {408, 429}
                or response.status_code >= 500
                or error_info.numeric_code in _RETRYABLE_ERROR_CODES
            )
            if rate_limited:
                self._metrics.increment_rate_limited(operation)
            if retryable and attempt < self._config.retry_max_attempts:
                self._retry(operation, attempt, f"http_{response.status_code}")
                continue
            raise MetaGraphFailure(
                (
                    MetaGraphFailureKind.RETRYABLE
                    if retryable
                    else MetaGraphFailureKind.PERMANENT
                ),
                code=error_info.safe_code,
                safe_message=(
                    "Meta is temporarily unavailable"
                    if retryable
                    else "Meta rejected the request"
                ),
            )
        raise RuntimeError("Meta retry loop completed without a result")

    def _retry(self, operation: MetaOperation, attempt: int, reason: str) -> None:
        self._metrics.increment_retry(operation, reason)
        delay = min(
            self._config.retry_base_seconds * (2 ** (attempt - 1)),
            self._config.retry_max_seconds,
        )
        self._sleeper(delay)


def _safe_graph_error(body: bytes, status_code: int) -> _MetaGraphErrorInfo:
    try:
        parsed = MetaGraphErrorEnvelope.model_validate_json(body)
    except ValidationError:
        return _MetaGraphErrorInfo(f"HTTP_{status_code}", None)
    code = str(parsed.error.code) if parsed.error.code is not None else None
    if code is None:
        return _MetaGraphErrorInfo(f"HTTP_{status_code}", None)
    if parsed.error.error_subcode is None:
        return _MetaGraphErrorInfo(code, parsed.error.code)
    return _MetaGraphErrorInfo(
        f"{code}:{parsed.error.error_subcode}",
        parsed.error.code,
    )


def _is_allowed_media_url(url: str) -> bool:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname is None:
        return False
    hostname = parsed.hostname.lower()
    return hostname == "facebook.com" or hostname.endswith(
        (".facebook.com", ".fbcdn.net", ".fbsbx.com")
    )
