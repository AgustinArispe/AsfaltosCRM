from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import (
    WhatsAppBroadcastRecipient,
    WhatsAppConversation,
    WhatsAppDirection,
    WhatsAppMessage,
    WhatsAppMessageStatusEvent,
    WhatsAppProviderState,
)
from app.services.customer_identity_service import acquire_advisory_locks
from app.services.errors import InvalidWhatsAppMessageError
from app.services.whatsapp_broadcast_projection_service import (
    recompute_broadcast_recipient_projection,
)
from app.services.whatsapp_projection_service import (
    later_datetime,
    recompute_response_projection,
)


@dataclass(frozen=True, slots=True)
class ProviderStatusInput:
    external_message_id: str
    state: WhatsAppProviderState
    occurred_at: datetime
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderStatusResult:
    event_id: int
    message_id: int | None
    created: bool


class WhatsAppStatusService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record(
        self,
        status_input: ProviderStatusInput,
        *,
        received_at: datetime | None = None,
    ) -> ProviderStatusResult:
        normalized = self._normalize(status_input)
        received = self._aware_utc(received_at or datetime.now(UTC))
        with self._session.begin():
            acquire_advisory_locks(
                self._session,
                (
                    (
                        "whatsapp-provider-message",
                        normalized.external_message_id,
                    ),
                ),
            )
            discovered_message = self._session.scalar(
                select(WhatsAppMessage).where(
                    WhatsAppMessage.external_message_id
                    == normalized.external_message_id
                )
            )
            if discovered_message is not None:
                message = self._message_graph_for_update(discovered_message.id)
                if message.direction is not WhatsAppDirection.OUTBOUND:
                    raise InvalidWhatsAppMessageError(
                        "Provider delivery states only apply to outbound messages"
                    )
            else:
                message = None

            statement = (
                insert(WhatsAppMessageStatusEvent)
                .values(
                    external_message_id=normalized.external_message_id,
                    provider_state=normalized.state,
                    occurred_at=normalized.occurred_at,
                    received_at=received,
                    provider_error_code=normalized.error_code,
                    provider_error_message=normalized.error_message,
                )
                .on_conflict_do_nothing(
                    constraint="uq_whatsapp_status_events_external_state_time"
                )
                .returning(WhatsAppMessageStatusEvent.id)
            )
            event_id = self._session.scalar(statement)
            created = event_id is not None
            if event_id is None:
                event = self._session.scalar(
                    select(WhatsAppMessageStatusEvent).where(
                        WhatsAppMessageStatusEvent.external_message_id
                        == normalized.external_message_id,
                        WhatsAppMessageStatusEvent.provider_state == normalized.state,
                        WhatsAppMessageStatusEvent.occurred_at
                        == normalized.occurred_at,
                    )
                )
                if event is None:
                    raise RuntimeError("Status-event upsert returned no row")
            else:
                event = self._session.get(WhatsAppMessageStatusEvent, event_id)
                if event is None:
                    raise RuntimeError("Created status event could not be loaded")

            if message is not None:
                event.message_id = message.id
                self.apply_event_in_transaction(message, event, now=received)
            self._session.flush()
            return ProviderStatusResult(
                event_id=event.id,
                message_id=message.id if message is not None else None,
                created=created,
            )

    def _message_graph_for_update(self, message_id: int) -> WhatsAppMessage:
        discovered = self._session.get(WhatsAppMessage, message_id)
        if discovered is None:
            raise RuntimeError("Persisted status Message disappeared")
        if discovered.broadcast_recipient_id is not None:
            recipient = self._session.scalar(
                select(WhatsAppBroadcastRecipient)
                .where(
                    WhatsAppBroadcastRecipient.id == discovered.broadcast_recipient_id
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if recipient is None:
                raise RuntimeError("Broadcast Message has no recipient")
        conversation = self._session.scalar(
            select(WhatsAppConversation)
            .where(WhatsAppConversation.id == discovered.conversation_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if conversation is None:
            raise RuntimeError("Persisted WhatsApp message has no conversation")
        message = self._session.scalar(
            select(WhatsAppMessage)
            .where(WhatsAppMessage.id == message_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if message is None:
            raise RuntimeError("Persisted status Message disappeared")
        return message

    def attach_pending_events_in_transaction(
        self,
        message: WhatsAppMessage,
        *,
        now: datetime,
    ) -> None:
        if message.external_message_id is None:
            return
        events = self._session.scalars(
            select(WhatsAppMessageStatusEvent)
            .where(
                WhatsAppMessageStatusEvent.external_message_id
                == message.external_message_id,
                WhatsAppMessageStatusEvent.message_id.is_(None),
            )
            .order_by(
                WhatsAppMessageStatusEvent.occurred_at,
                WhatsAppMessageStatusEvent.id,
            )
            .with_for_update()
        )
        for event in events:
            event.message_id = message.id
            self.apply_event_in_transaction(message, event, now=now)

    def apply_event_in_transaction(
        self,
        message: WhatsAppMessage,
        event: WhatsAppMessageStatusEvent,
        *,
        now: datetime,
    ) -> None:
        self._record_evidence_timestamp(message, event)
        if self._should_replace_effective_state(message, event):
            message.provider_state = event.provider_state
            message.provider_status_at = event.occurred_at
            if event.provider_state is WhatsAppProviderState.FAILED:
                message.provider_error_code = event.provider_error_code
                message.provider_error_message = event.provider_error_message
        message.updated_at = later_datetime(
            message.updated_at,
            self._aware_utc(now),
        )
        conversation = self._session.get(
            WhatsAppConversation,
            message.conversation_id,
        )
        if conversation is None:
            raise RuntimeError("Persisted WhatsApp message has no conversation")
        recompute_response_projection(
            self._session,
            conversation,
            now=now,
        )
        if message.broadcast_recipient_id is not None:
            recipient = self._session.get(
                WhatsAppBroadcastRecipient,
                message.broadcast_recipient_id,
            )
            if recipient is None:
                raise RuntimeError("Broadcast Message has no recipient")
            recompute_broadcast_recipient_projection(
                self._session,
                recipient,
                now=now,
            )

    @staticmethod
    def _record_evidence_timestamp(
        message: WhatsAppMessage,
        event: WhatsAppMessageStatusEvent,
    ) -> None:
        if event.provider_state is WhatsAppProviderState.SENT:
            message.sent_at = WhatsAppStatusService._earliest(
                message.sent_at,
                event.occurred_at,
            )
        elif event.provider_state is WhatsAppProviderState.DELIVERED:
            message.delivered_at = WhatsAppStatusService._earliest(
                message.delivered_at,
                event.occurred_at,
            )
        elif event.provider_state is WhatsAppProviderState.READ:
            message.read_at = WhatsAppStatusService._earliest(
                message.read_at,
                event.occurred_at,
            )
        elif event.provider_state is WhatsAppProviderState.FAILED:
            message.failed_at = WhatsAppStatusService._earliest(
                message.failed_at,
                event.occurred_at,
            )

    @staticmethod
    def _should_replace_effective_state(
        message: WhatsAppMessage,
        event: WhatsAppMessageStatusEvent,
    ) -> bool:
        if message.provider_status_at is None or message.provider_state is None:
            return True
        if (
            message.provider_state
            in {WhatsAppProviderState.DELIVERED, WhatsAppProviderState.READ}
            and event.provider_state is WhatsAppProviderState.FAILED
        ):
            return False
        if event.occurred_at > message.provider_status_at:
            return True
        if event.occurred_at < message.provider_status_at:
            return False
        return WhatsAppStatusService._state_rank(
            event.provider_state
        ) > WhatsAppStatusService._state_rank(message.provider_state)

    @staticmethod
    def _state_rank(state: WhatsAppProviderState) -> int:
        ranks = {
            WhatsAppProviderState.FAILED: 0,
            WhatsAppProviderState.SENT: 1,
            WhatsAppProviderState.DELIVERED: 2,
            WhatsAppProviderState.READ: 3,
            WhatsAppProviderState.RECEIVED: -1,
        }
        return ranks[state]

    @staticmethod
    def _earliest(
        current: datetime | None,
        candidate: datetime,
    ) -> datetime:
        if current is None or candidate < current:
            return candidate
        return current

    @staticmethod
    def _normalize(status_input: ProviderStatusInput) -> ProviderStatusInput:
        external_id = status_input.external_message_id.strip()
        if not external_id:
            raise InvalidWhatsAppMessageError("External message ID is required")
        if status_input.state is WhatsAppProviderState.RECEIVED:
            raise InvalidWhatsAppMessageError(
                "RECEIVED is not an outbound delivery state"
            )
        code = WhatsAppStatusService._optional_text(status_input.error_code)
        message = WhatsAppStatusService._optional_text(status_input.error_message)
        return ProviderStatusInput(
            external_message_id=external_id,
            state=status_input.state,
            occurred_at=WhatsAppStatusService._aware_utc(status_input.occurred_at),
            error_code=code,
            error_message=message,
        )

    @staticmethod
    def _optional_text(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _aware_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Datetime must be timezone-aware")
        return value.astimezone(UTC)
