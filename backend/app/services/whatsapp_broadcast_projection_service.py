from datetime import datetime

from sqlalchemy.orm import Session

from app.models import (
    WhatsAppBroadcastRecipient,
    WhatsAppBroadcastRecipientStatus,
    WhatsAppDispatchState,
    WhatsAppMessage,
    WhatsAppProviderState,
)
from app.services.whatsapp_projection_service import later_datetime


def sync_broadcast_recipient_from_message(
    session: Session,
    message: WhatsAppMessage,
    *,
    now: datetime,
) -> None:
    if message.broadcast_recipient_id is None:
        return
    recipient = session.get(WhatsAppBroadcastRecipient, message.broadcast_recipient_id)
    if recipient is None:
        raise RuntimeError("Broadcast Message has no recipient")
    recipient.accepted_at = later_datetime(recipient.accepted_at, message.accepted_at)
    recipient.sent_at = later_datetime(recipient.sent_at, message.sent_at)
    recipient.delivered_at = later_datetime(
        recipient.delivered_at,
        message.delivered_at,
    )
    recipient.read_at = later_datetime(recipient.read_at, message.read_at)
    recipient.failed_at = later_datetime(recipient.failed_at, message.failed_at)
    recipient.latest_attempt_at = later_datetime(
        recipient.latest_attempt_at,
        message.created_at,
    )
    if recipient.first_attempt_at is None:
        recipient.first_attempt_at = message.created_at
    recipient.safe_error_code = message.provider_error_code
    recipient.safe_error_message = message.provider_error_message
    recipient.status = _recipient_status(message)
    recipient.updated_at = later_datetime(recipient.updated_at, now)


def _recipient_status(message: WhatsAppMessage) -> WhatsAppBroadcastRecipientStatus:
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
    return WhatsAppBroadcastRecipientStatus.IN_PROGRESS
