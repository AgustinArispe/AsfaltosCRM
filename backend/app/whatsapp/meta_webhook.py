from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from hmac import compare_digest
from hmac import new as hmac_new
from typing import Never

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.models import WhatsAppMessageType, WhatsAppProviderState
from app.whatsapp.meta_observability import (
    MetaMetrics,
    MetaWebhookEventKind,
    MetaWebhookOutcome,
)
from app.whatsapp.webhook_contracts import (
    ProviderIgnoredEvent,
    ProviderInboundAttachment,
    ProviderInboundEvent,
    ProviderStatusEvent,
    ProviderWebhookEvent,
    ProviderWebhookMappingError,
)


class _MetaProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = None


class _MetaContact(BaseModel):
    model_config = ConfigDict(extra="ignore")

    wa_id: str | None = None
    profile: _MetaProfile | None = None


class _MetaMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    phone_number_id: str | None = None


class _MetaText(BaseModel):
    model_config = ConfigDict(extra="ignore")

    body: str | None = None


class _MetaImage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    mime_type: str | None = None
    caption: str | None = None


class _MetaDocument(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    mime_type: str | None = None
    filename: str | None = None
    caption: str | None = None


class _MetaInboundMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    from_phone: str | None = Field(default=None, alias="from")
    timestamp: str | None = None
    type: str | None = None
    text: _MetaText | None = None
    image: _MetaImage | None = None
    document: _MetaDocument | None = None


class _MetaStatusErrorData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    details: str | None = None


class _MetaStatusError(BaseModel):
    model_config = ConfigDict(extra="ignore")

    code: int | None = None
    error_data: _MetaStatusErrorData | None = None


class _MetaStatus(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    status: str | None = None
    timestamp: str | None = None
    errors: tuple[_MetaStatusError, ...] = ()


class _MetaWebhookValue(BaseModel):
    model_config = ConfigDict(extra="ignore")

    messaging_product: str | None = None
    metadata: _MetaMetadata | None = None
    contacts: tuple[_MetaContact, ...] = ()
    messages: tuple[_MetaInboundMessage, ...] = ()
    statuses: tuple[_MetaStatus, ...] = ()


class _MetaChange(BaseModel):
    model_config = ConfigDict(extra="ignore")

    field: str | None = None
    value: _MetaWebhookValue = _MetaWebhookValue()


class _MetaEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    changes: tuple[_MetaChange, ...] = ()


class _MetaWebhookEnvelope(BaseModel):
    model_config = ConfigDict(extra="ignore")

    object: str | None = None
    entry: tuple[_MetaEntry, ...] = ()


class MetaWebhookVerifier:
    def __init__(self, *, verify_token: str, app_secret: str) -> None:
        self._verify_token = verify_token
        self._app_secret = app_secret.encode()

    def verify_challenge(
        self,
        *,
        mode: str | None,
        verify_token: str | None,
        challenge: str | None,
    ) -> str | None:
        if (
            mode != "subscribe"
            or verify_token is None
            or challenge is None
            or not compare_digest(verify_token, self._verify_token)
        ):
            return None
        return challenge

    def verify_signature(self, raw_body: bytes, signature: str | None) -> bool:
        if signature is None or not signature.startswith("sha256="):
            return False
        supplied = signature.removeprefix("sha256=")
        if len(supplied) != 64:
            return False
        expected = hmac_new(self._app_secret, raw_body, sha256).hexdigest()
        return compare_digest(supplied, expected)


class MetaWebhookMapper:
    def __init__(
        self,
        *,
        waba_id: str,
        phone_number_id: str,
        metrics: MetaMetrics,
    ) -> None:
        self._waba_id = waba_id
        self._phone_number_id = phone_number_id
        self._metrics = metrics

    def map_events(self, raw_body: bytes) -> tuple[ProviderWebhookEvent, ...]:
        try:
            envelope = _MetaWebhookEnvelope.model_validate_json(raw_body)
        except ValidationError as error:
            self._metrics.increment_mapping_failure("webhook_envelope")
            raise ProviderWebhookMappingError(
                "Meta webhook payload is invalid"
            ) from error
        events: list[ProviderWebhookEvent] = []
        if envelope.object != "whatsapp_business_account":
            return (self._ignored("object"),)
        for entry in envelope.entry:
            if entry.id != self._waba_id:
                events.append(self._ignored("account"))
                continue
            for change in entry.changes:
                if change.field != "messages":
                    events.append(self._ignored("change"))
                    continue
                metadata = change.value.metadata
                if (
                    change.value.messaging_product != "whatsapp"
                    or metadata is None
                    or metadata.phone_number_id != self._phone_number_id
                ):
                    events.append(self._ignored("phone_number"))
                    continue
                for message in change.value.messages:
                    events.append(self._map_message(message, change.value.contacts))
                for status in change.value.statuses:
                    events.append(self._map_status(status))
                if not change.value.messages and not change.value.statuses:
                    events.append(self._ignored("empty_messages_change"))
        if not events:
            events.append(self._ignored("empty_envelope"))
        return tuple(events)

    def _map_message(
        self,
        message: _MetaInboundMessage,
        contacts: tuple[_MetaContact, ...],
    ) -> ProviderWebhookEvent:
        message_type = (message.type or "").lower()
        if message_type not in {"text", "image", "document"}:
            return self._ignored("message_type")
        external_id = self._required(message.id, "message ID")
        sender = self._required(message.from_phone, "message sender")
        timestamp = self._timestamp(message.timestamp, "message")
        contact = next((item for item in contacts if item.wa_id == sender), None)
        display_name = (
            contact.profile.name
            if contact is not None and contact.profile is not None
            else None
        )
        attachment: ProviderInboundAttachment | None = None
        body: str | None
        if message_type == "text":
            if message.text is None:
                self._mapping_failure("inbound_text")
            body = self._required(message.text.body, "message body")
            domain_type = WhatsAppMessageType.TEXT
            event_kind = MetaWebhookEventKind.INBOUND_TEXT
        elif message_type == "image":
            if message.image is None:
                self._mapping_failure("inbound_image")
            body = message.image.caption
            attachment = ProviderInboundAttachment(
                provider_media_id=self._required(message.image.id, "image media ID"),
                mime_type=_optional_text(message.image.mime_type),
                filename=None,
                size_bytes=None,
            )
            domain_type = WhatsAppMessageType.IMAGE
            event_kind = MetaWebhookEventKind.INBOUND_IMAGE
        else:
            if message.document is None:
                self._mapping_failure("inbound_document")
            body = message.document.caption
            attachment = ProviderInboundAttachment(
                provider_media_id=self._required(
                    message.document.id,
                    "document media ID",
                ),
                mime_type=_optional_text(message.document.mime_type),
                filename=_optional_text(message.document.filename),
                size_bytes=None,
            )
            domain_type = WhatsAppMessageType.DOCUMENT
            event_kind = MetaWebhookEventKind.INBOUND_DOCUMENT
        self._metrics.increment_webhook_event(
            event_kind,
            MetaWebhookOutcome.MAPPED,
        )
        return ProviderInboundEvent(
            external_message_id=external_id,
            external_phone=sender,
            provider_contact_id=contact.wa_id if contact is not None else sender,
            display_name=_optional_text(display_name),
            message_type=domain_type,
            body=_optional_text(body),
            provider_message_at=timestamp,
            attachment=attachment,
        )

    def _map_status(self, status: _MetaStatus) -> ProviderWebhookEvent:
        raw_state = (status.status or "").lower()
        states = {
            "sent": WhatsAppProviderState.SENT,
            "delivered": WhatsAppProviderState.DELIVERED,
            "read": WhatsAppProviderState.READ,
            "failed": WhatsAppProviderState.FAILED,
        }
        state = states.get(raw_state)
        if state is None:
            return self._ignored("status")
        first_error = status.errors[0] if status.errors else None
        error_code = (
            str(first_error.code)
            if first_error is not None and first_error.code is not None
            else None
        )
        self._metrics.increment_webhook_event(
            MetaWebhookEventKind.STATUS,
            MetaWebhookOutcome.MAPPED,
        )
        return ProviderStatusEvent(
            external_message_id=self._required(status.id, "status message ID"),
            state=state,
            occurred_at=self._timestamp(status.timestamp, "status"),
            error_code=error_code if state is WhatsAppProviderState.FAILED else None,
            error_message=(
                "Meta reported message delivery failure"
                if state is WhatsAppProviderState.FAILED
                else None
            ),
        )

    def _ignored(self, category: str) -> ProviderIgnoredEvent:
        self._metrics.increment_webhook_event(
            MetaWebhookEventKind.UNKNOWN,
            MetaWebhookOutcome.IGNORED,
        )
        return ProviderIgnoredEvent(category=category)

    def _required(self, value: str | None, field: str) -> str:
        normalized = value.strip() if value is not None else ""
        if not normalized:
            self._mapping_failure(field)
        return normalized

    def _timestamp(self, value: str | None, payload_kind: str) -> datetime:
        try:
            timestamp = _nonnegative_timestamp(value)
            return datetime.fromtimestamp(timestamp, tz=UTC)
        except (ValueError, OverflowError) as error:
            self._metrics.increment_mapping_failure(payload_kind)
            raise ProviderWebhookMappingError(
                "Meta webhook timestamp is invalid"
            ) from error

    def _mapping_failure(self, payload_kind: str) -> Never:
        self._metrics.increment_mapping_failure(payload_kind)
        self._metrics.increment_webhook_event(
            MetaWebhookEventKind.UNKNOWN,
            MetaWebhookOutcome.FAILED,
        )
        raise ProviderWebhookMappingError("Meta webhook payload is invalid")


class MetaWebhookIntegration:
    def __init__(
        self,
        verifier: MetaWebhookVerifier,
        mapper: MetaWebhookMapper,
    ) -> None:
        self._verifier = verifier
        self._mapper = mapper

    def verify_challenge(
        self,
        *,
        mode: str | None,
        verify_token: str | None,
        challenge: str | None,
    ) -> str | None:
        return self._verifier.verify_challenge(
            mode=mode,
            verify_token=verify_token,
            challenge=challenge,
        )

    def verify_signature(self, raw_body: bytes, signature: str | None) -> bool:
        return self._verifier.verify_signature(raw_body, signature)

    def map_events(self, raw_body: bytes) -> tuple[ProviderWebhookEvent, ...]:
        return self._mapper.map_events(raw_body)


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _nonnegative_timestamp(value: str | None) -> int:
    timestamp = int(value) if value is not None else -1
    if timestamp < 0:
        raise ValueError("timestamp must be nonnegative")
    return timestamp
