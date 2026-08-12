from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    WhatsAppBroadcastRecipient,
    WhatsAppBroadcastRecipientStatus,
    WhatsAppDispatchState,
    WhatsAppMessage,
    WhatsAppProviderState,
)
from app.services.whatsapp_projection_service import later_datetime


def recompute_broadcast_recipient_projection(
    session: Session,
    recipient: WhatsAppBroadcastRecipient,
    *,
    now: datetime,
) -> None:
    messages = tuple(
        session.scalars(
            select(WhatsAppMessage)
            .where(WhatsAppMessage.broadcast_recipient_id == recipient.id)
            .order_by(WhatsAppMessage.id)
        )
    )
    if not messages:
        return

    latest = messages[-1]
    recipient.first_attempt_at = messages[0].created_at
    recipient.latest_attempt_at = latest.created_at
    recipient.accepted_at = _latest_timestamp(
        tuple(message.accepted_at for message in messages)
    )
    recipient.sent_at = _latest_timestamp(
        tuple(message.sent_at for message in messages)
    )
    recipient.delivered_at = _latest_timestamp(
        tuple(message.delivered_at for message in messages)
    )
    recipient.read_at = _latest_timestamp(
        tuple(message.read_at for message in messages)
    )
    recipient.failed_at = _latest_timestamp(
        tuple(message.failed_at for message in messages)
    )
    recipient.safe_error_code = latest.provider_error_code
    recipient.safe_error_message = latest.provider_error_message
    if not (
        recipient.status is WhatsAppBroadcastRecipientStatus.BLOCKED
        and recipient.reason_code is not None
        and latest.dispatch_state is WhatsAppDispatchState.PENDING
    ):
        recipient.status = _recipient_status(recipient, latest)
    recipient.updated_at = later_datetime(recipient.updated_at, now)


def _latest_timestamp(values: tuple[datetime | None, ...]) -> datetime | None:
    latest: datetime | None = None
    for value in values:
        latest = later_datetime(latest, value)
    return latest


def _recipient_status(
    recipient: WhatsAppBroadcastRecipient,
    message: WhatsAppMessage,
) -> WhatsAppBroadcastRecipientStatus:
    if message.provider_state is WhatsAppProviderState.READ:
        return WhatsAppBroadcastRecipientStatus.READ
    if message.provider_state is WhatsAppProviderState.DELIVERED:
        return WhatsAppBroadcastRecipientStatus.DELIVERED
    if message.provider_state is WhatsAppProviderState.SENT:
        return WhatsAppBroadcastRecipientStatus.SENT
    if message.provider_state is WhatsAppProviderState.FAILED:
        return WhatsAppBroadcastRecipientStatus.FAILED
    if message.dispatch_state is WhatsAppDispatchState.UNKNOWN:
        return WhatsAppBroadcastRecipientStatus.UNKNOWN
    if message.dispatch_state is WhatsAppDispatchState.DEFINITIVE_FAILED:
        return WhatsAppBroadcastRecipientStatus.FAILED
    if message.dispatch_state is WhatsAppDispatchState.ACCEPTED:
        return WhatsAppBroadcastRecipientStatus.ACCEPTED
    if (
        message.dispatch_state is WhatsAppDispatchState.PENDING
        and recipient.claim_token is None
    ):
        return WhatsAppBroadcastRecipientStatus.READY
    return WhatsAppBroadcastRecipientStatus.IN_PROGRESS
