from __future__ import annotations

from enum import StrEnum
from typing import Protocol


class MetaOperation(StrEnum):
    SEND_TEXT = "send_text"
    SEND_IMAGE = "send_image"
    SEND_DOCUMENT = "send_document"
    SEND_TEMPLATE = "send_template"
    MEDIA_UPLOAD = "media_upload"
    MEDIA_RESOLVE = "media_resolve"
    MEDIA_DOWNLOAD = "media_download"
    TEMPLATE_LIST = "template_list"


class MetaHttpOutcome(StrEnum):
    SUCCESS = "success"
    PROVIDER_ERROR = "provider_error"
    TRANSPORT_ERROR = "transport_error"
    MAPPING_ERROR = "mapping_error"


class MetaWebhookEventKind(StrEnum):
    INBOUND_TEXT = "inbound_text"
    INBOUND_IMAGE = "inbound_image"
    INBOUND_DOCUMENT = "inbound_document"
    STATUS = "status"
    UNKNOWN = "unknown"


class MetaWebhookOutcome(StrEnum):
    MAPPED = "mapped"
    IGNORED = "ignored"
    FAILED = "failed"


class MetaMetrics(Protocol):
    def observe_http(
        self,
        operation: MetaOperation,
        status_class: str,
        outcome: MetaHttpOutcome,
        duration_seconds: float,
    ) -> None: ...

    def increment_retry(self, operation: MetaOperation, reason: str) -> None: ...

    def increment_transport_failure(
        self,
        operation: MetaOperation,
        failure_kind: str,
    ) -> None: ...

    def increment_rate_limited(self, operation: MetaOperation) -> None: ...

    def increment_mapping_failure(self, payload_kind: str) -> None: ...

    def increment_webhook_event(
        self,
        event_kind: MetaWebhookEventKind,
        outcome: MetaWebhookOutcome,
    ) -> None: ...

    def increment_template_sync(self, outcome: str) -> None: ...


class NullMetaMetrics:
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
        del payload_kind

    def increment_webhook_event(
        self,
        event_kind: MetaWebhookEventKind,
        outcome: MetaWebhookOutcome,
    ) -> None:
        del event_kind, outcome

    def increment_template_sync(self, outcome: str) -> None:
        del outcome
