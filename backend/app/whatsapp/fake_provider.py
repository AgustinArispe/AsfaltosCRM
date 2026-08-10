from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.models import WhatsAppProviderState
from app.whatsapp.contracts import (
    ProviderDeliveryEvent,
    ProviderErrorDetails,
    ProviderErrorKind,
    ProviderMediaPayload,
    ProviderMediaReference,
    ProviderSendResult,
    ProviderTemplateSnapshot,
    RecordedProviderRequest,
    SendDocumentRequest,
    SendImageRequest,
    SendTemplateRequest,
    SendTextRequest,
    WhatsAppProviderError,
    WindowDecision,
    WindowEvaluationContext,
)


class FakeWhatsAppProvider:
    def __init__(
        self,
        *,
        now: datetime | None = None,
        freeform_window: timedelta | None = None,
        templates: tuple[ProviderTemplateSnapshot, ...] = (),
    ) -> None:
        self._now = now or datetime.now(UTC)
        self._freeform_window = freeform_window
        self._templates = templates
        self._next_external_id = 1
        self._behaviors: dict[UUID, ProviderErrorDetails] = {}
        self._media: dict[str, ProviderMediaPayload] = {}
        self.requests: list[RecordedProviderRequest] = []
        self.delivery_events: list[ProviderDeliveryEvent] = []

    def set_now(self, now: datetime) -> None:
        self._now = self._aware_utc(now)

    def configure_error(
        self,
        client_generated_id: UUID,
        kind: ProviderErrorKind,
        *,
        code: str | None = None,
        safe_message: str = "Fake provider failure",
    ) -> None:
        retryable = kind in {
            ProviderErrorKind.RETRYABLE_FAILURE,
            ProviderErrorKind.TIMEOUT_BEFORE_ACCEPTANCE,
            ProviderErrorKind.TIMEOUT_UNKNOWN_ACCEPTANCE,
        }
        self._behaviors[client_generated_id] = ProviderErrorDetails(
            kind=kind,
            code=code,
            safe_message=safe_message,
            retryable=retryable,
            acceptance_unknown=(kind is ProviderErrorKind.TIMEOUT_UNKNOWN_ACCEPTANCE),
        )

    def add_media(
        self,
        provider_media_id: str,
        payload: ProviderMediaPayload,
    ) -> None:
        self._media[provider_media_id] = payload

    def set_templates(
        self,
        templates: tuple[ProviderTemplateSnapshot, ...],
    ) -> None:
        self._templates = templates

    def send_text(self, request: SendTextRequest) -> ProviderSendResult:
        return self._send(request)

    def send_image(self, request: SendImageRequest) -> ProviderSendResult:
        return self._send(request)

    def send_document(self, request: SendDocumentRequest) -> ProviderSendResult:
        return self._send(request)

    def send_template(self, request: SendTemplateRequest) -> ProviderSendResult:
        return self._send(request)

    def download_media(
        self,
        reference: ProviderMediaReference,
    ) -> ProviderMediaPayload:
        if reference.provider_media_id is None:
            raise WhatsAppProviderError(
                ProviderErrorDetails(
                    kind=ProviderErrorKind.PERMANENT_FAILURE,
                    code="FAKE_MEDIA_ID_REQUIRED",
                    safe_message="Fake media requires a provider media ID",
                    retryable=False,
                    acceptance_unknown=False,
                )
            )
        payload = self._media.get(reference.provider_media_id)
        if payload is None:
            raise WhatsAppProviderError(
                ProviderErrorDetails(
                    kind=ProviderErrorKind.PERMANENT_FAILURE,
                    code="FAKE_MEDIA_NOT_FOUND",
                    safe_message="Fake media was not found",
                    retryable=False,
                    acceptance_unknown=False,
                )
            )
        return payload

    def list_templates(self) -> tuple[ProviderTemplateSnapshot, ...]:
        return self._templates

    def evaluate_window(
        self,
        context: WindowEvaluationContext,
    ) -> WindowDecision:
        now = self._aware_utc(context.now)
        last_inbound = (
            self._aware_utc(context.last_inbound_at)
            if context.last_inbound_at is not None
            else None
        )
        if last_inbound is None or self._freeform_window is None:
            return WindowDecision(
                can_send_freeform=False,
                window_expires_at=None,
            )
        expires_at = last_inbound + self._freeform_window
        return WindowDecision(
            can_send_freeform=now < expires_at,
            window_expires_at=expires_at,
        )

    def emit_delivery_events(
        self,
        external_message_id: str,
        states: tuple[WhatsAppProviderState, ...],
        *,
        duplicate: bool = False,
        occurred_at: datetime | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> tuple[ProviderDeliveryEvent, ...]:
        timestamp = self._aware_utc(occurred_at or self._now)
        events = tuple(
            ProviderDeliveryEvent(
                external_message_id=external_message_id,
                state=state,
                occurred_at=timestamp + timedelta(seconds=index),
                error_code=(
                    error_code if state is WhatsAppProviderState.FAILED else None
                ),
                error_message=(
                    error_message if state is WhatsAppProviderState.FAILED else None
                ),
            )
            for index, state in enumerate(states)
        )
        self.delivery_events.extend(events)
        if duplicate:
            self.delivery_events.extend(events)
            return events + events
        return events

    def _send(self, request: RecordedProviderRequest) -> ProviderSendResult:
        self.requests.append(request)
        behavior = self._behaviors.get(request.client_generated_id)
        if behavior is not None:
            raise WhatsAppProviderError(behavior)
        external_id = f"fake-message-{self._next_external_id:06d}"
        self._next_external_id += 1
        return ProviderSendResult(
            external_message_id=external_id,
            accepted_at=self._now,
            initial_state=WhatsAppProviderState.SENT,
        )

    @staticmethod
    def _aware_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Datetime must be timezone-aware")
        return value.astimezone(UTC)
