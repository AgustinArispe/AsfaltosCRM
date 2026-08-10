from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.models import WhatsAppMessageType, WhatsAppProviderState


@dataclass(frozen=True, slots=True)
class ProviderInboundAttachment:
    provider_media_id: str
    mime_type: str | None
    filename: str | None
    size_bytes: int | None


@dataclass(frozen=True, slots=True)
class ProviderInboundEvent:
    external_message_id: str
    external_phone: str
    provider_contact_id: str | None
    display_name: str | None
    message_type: WhatsAppMessageType
    body: str | None
    provider_message_at: datetime
    attachment: ProviderInboundAttachment | None = None


@dataclass(frozen=True, slots=True)
class ProviderStatusEvent:
    external_message_id: str
    state: WhatsAppProviderState
    occurred_at: datetime
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderIgnoredEvent:
    category: str


ProviderWebhookEvent = ProviderInboundEvent | ProviderStatusEvent | ProviderIgnoredEvent


class ProviderWebhookMappingError(Exception):
    """Raised when a recognized provider payload cannot be mapped safely."""


class ProviderWebhook(Protocol):
    def verify_challenge(
        self,
        *,
        mode: str | None,
        verify_token: str | None,
        challenge: str | None,
    ) -> str | None: ...

    def verify_signature(self, raw_body: bytes, signature: str | None) -> bool: ...

    def map_events(self, raw_body: bytes) -> tuple[ProviderWebhookEvent, ...]: ...
