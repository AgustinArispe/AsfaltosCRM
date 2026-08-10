from datetime import UTC, datetime
from typing import overload

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    WhatsAppConversation,
    WhatsAppDirection,
    WhatsAppDispatchState,
    WhatsAppMessage,
    WhatsAppProviderState,
)


def recompute_response_projection(
    session: Session,
    conversation: WhatsAppConversation,
    *,
    now: datetime,
) -> None:
    """Rebuild response-related inbox fields from persisted message evidence."""
    valid_outbound_at = session.scalar(
        select(func.max(WhatsAppMessage.accepted_at)).where(
            WhatsAppMessage.conversation_id == conversation.id,
            WhatsAppMessage.direction == WhatsAppDirection.OUTBOUND,
            WhatsAppMessage.sent_by_user_id.is_not(None),
            WhatsAppMessage.dispatch_state == WhatsAppDispatchState.ACCEPTED,
            WhatsAppMessage.provider_state != WhatsAppProviderState.FAILED,
        )
    )
    conversation.last_outbound_at = valid_outbound_at

    inbound_time = func.coalesce(
        WhatsAppMessage.provider_message_at,
        WhatsAppMessage.created_at,
    )
    unanswered_filters = [
        WhatsAppMessage.conversation_id == conversation.id,
        WhatsAppMessage.direction == WhatsAppDirection.INBOUND,
    ]
    if valid_outbound_at is not None:
        unanswered_filters.append(inbound_time > valid_outbound_at)
    waiting_since = session.scalar(
        select(func.min(inbound_time)).where(*unanswered_filters)
    )
    conversation.waiting_for_response = waiting_since is not None
    conversation.waiting_since_at = waiting_since
    conversation.updated_at = later_datetime(
        conversation.updated_at,
        _aware_utc(now),
    )


@overload
def later_datetime(
    current: datetime,
    candidate: datetime | None,
) -> datetime: ...


@overload
def later_datetime(
    current: None,
    candidate: datetime | None,
) -> datetime | None: ...


def later_datetime(
    current: datetime | None,
    candidate: datetime | None,
) -> datetime | None:
    if candidate is None:
        return current
    if current is None or candidate > current:
        return candidate
    return current


def earlier_datetime(
    current: datetime | None,
    candidate: datetime,
) -> datetime:
    if current is None or candidate < current:
        return candidate
    return current


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Datetime must be timezone-aware")
    return value.astimezone(UTC)
