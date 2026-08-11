from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from app.models import WhatsAppProviderState


class ProviderErrorKind(StrEnum):
    PERMANENT_FAILURE = "PERMANENT_FAILURE"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    TIMEOUT_BEFORE_ACCEPTANCE = "TIMEOUT_BEFORE_ACCEPTANCE"
    TIMEOUT_UNKNOWN_ACCEPTANCE = "TIMEOUT_UNKNOWN_ACCEPTANCE"


class TemplateHeaderType(StrEnum):
    NONE = "NONE"
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    DOCUMENT = "DOCUMENT"


@dataclass(frozen=True, slots=True)
class ProviderRecipient:
    phone: str


@dataclass(frozen=True, slots=True)
class ProviderMediaReference:
    provider_media_id: str | None
    storage_key: str | None
    mime_type: str | None
    filename: str | None

    def __post_init__(self) -> None:
        if self.provider_media_id is None and self.storage_key is None:
            raise ValueError("A provider media ID or storage key is required")


@dataclass(frozen=True, slots=True)
class SendTextRequest:
    recipient: ProviderRecipient
    client_generated_id: UUID
    text: str


@dataclass(frozen=True, slots=True)
class SendImageRequest:
    recipient: ProviderRecipient
    client_generated_id: UUID
    media: ProviderMediaReference
    caption: str | None


@dataclass(frozen=True, slots=True)
class SendDocumentRequest:
    recipient: ProviderRecipient
    client_generated_id: UUID
    media: ProviderMediaReference
    caption: str | None


@dataclass(frozen=True, slots=True)
class TemplateParameter:
    name: str
    value: str


@dataclass(frozen=True, slots=True)
class SendTemplateRequest:
    recipient: ProviderRecipient
    client_generated_id: UUID
    template_name: str
    language: str
    parameters: tuple[TemplateParameter, ...]
    header_media: ProviderMediaReference | None = None


@dataclass(frozen=True, slots=True)
class ProviderSendResult:
    external_message_id: str
    accepted_at: datetime
    initial_state: WhatsAppProviderState | None


@dataclass(frozen=True, slots=True)
class ProviderMediaPayload:
    content: bytes
    mime_type: str
    filename: str | None


@dataclass(frozen=True, slots=True)
class ProviderTemplateSnapshot:
    external_id: str
    name: str
    language: str
    category: str
    status: str
    header_type: TemplateHeaderType
    parameter_names: tuple[str, ...] = ()
    header_media_required: bool = False
    supported_for_send: bool = True


@dataclass(frozen=True, slots=True)
class WindowEvaluationContext:
    last_inbound_at: datetime | None
    now: datetime


@dataclass(frozen=True, slots=True)
class WindowDecision:
    can_send_freeform: bool
    window_expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class ProviderErrorDetails:
    kind: ProviderErrorKind
    code: str | None
    safe_message: str
    retryable: bool
    acceptance_unknown: bool


class WhatsAppProviderError(Exception):
    def __init__(self, details: ProviderErrorDetails) -> None:
        self.details = details
        super().__init__(details.safe_message)


class WhatsAppProvider(Protocol):
    def send_text(self, request: SendTextRequest) -> ProviderSendResult: ...

    def send_image(self, request: SendImageRequest) -> ProviderSendResult: ...

    def send_document(self, request: SendDocumentRequest) -> ProviderSendResult: ...

    def send_template(self, request: SendTemplateRequest) -> ProviderSendResult: ...

    def download_media(
        self,
        reference: ProviderMediaReference,
    ) -> ProviderMediaPayload: ...

    def list_templates(self) -> tuple[ProviderTemplateSnapshot, ...]: ...

    def evaluate_window(
        self,
        context: WindowEvaluationContext,
    ) -> WindowDecision: ...


RecordedProviderRequest = (
    SendTextRequest | SendImageRequest | SendDocumentRequest | SendTemplateRequest
)


@dataclass(frozen=True, slots=True)
class ProviderDeliveryEvent:
    external_message_id: str
    state: WhatsAppProviderState
    occurred_at: datetime
    error_code: str | None = None
    error_message: str | None = None
