from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import UTC, datetime
from hashlib import sha256
from hmac import compare_digest, digest
from typing import Never

from app.services.errors import InvalidWhatsAppCursorError
from app.services.whatsapp_query_observability import (
    CursorRejectionMeasurement,
    WhatsAppCursorKind,
    WhatsAppCursorRejectionReason,
    WhatsAppQueryMetrics,
)
from app.services.whatsapp_query_projections import (
    ConversationPageCursor,
    MessagePageCursor,
    ResourceChangeCursor,
)

_CURSOR_VERSION = "1"


class WhatsAppCursorCodec:
    def __init__(self, secret: str, metrics: WhatsAppQueryMetrics) -> None:
        if len(secret) < 32:
            raise ValueError("Cursor secret must contain at least 32 characters")
        self._secret = secret.encode()
        self._metrics = metrics

    def encode_conversation_page(self, cursor: ConversationPageCursor) -> str:
        return self._encode(
            (
                _CURSOR_VERSION,
                "cp",
                _datetime_value(cursor.snapshot_at),
                "1" if cursor.waiting_for_response else "0",
                str(cursor.unread_count),
                (
                    _datetime_value(cursor.last_message_at)
                    if cursor.last_message_at is not None
                    else ""
                ),
                str(cursor.conversation_id),
            )
        )

    def decode_conversation_page(self, token: str) -> ConversationPageCursor:
        kind = WhatsAppCursorKind.CONVERSATION_PAGE
        values = self._decode(token, "cp", 7, kind)
        try:
            waiting = _bool_value(values[3])
            unread_count = _nonnegative_int(values[4])
            last_message_at = _datetime_from_value(values[5]) if values[5] else None
            return ConversationPageCursor(
                snapshot_at=_datetime_from_value(values[2]),
                waiting_for_response=waiting,
                unread_count=unread_count,
                last_message_at=last_message_at,
                conversation_id=_positive_int(values[6]),
            )
        except ValueError as error:
            self._reject(kind, WhatsAppCursorRejectionReason.INVALID_VALUE, error)

    def encode_message_page(self, cursor: MessagePageCursor) -> str:
        return self._encode(
            (
                _CURSOR_VERSION,
                "mp",
                _datetime_value(cursor.snapshot_at),
                _datetime_value(cursor.message_at),
                str(cursor.message_id),
            )
        )

    def decode_message_page(self, token: str) -> MessagePageCursor:
        kind = WhatsAppCursorKind.MESSAGE_PAGE
        values = self._decode(token, "mp", 5, kind)
        try:
            return MessagePageCursor(
                snapshot_at=_datetime_from_value(values[2]),
                message_at=_datetime_from_value(values[3]),
                message_id=_positive_int(values[4]),
            )
        except ValueError as error:
            self._reject(kind, WhatsAppCursorRejectionReason.INVALID_VALUE, error)

    def encode_resource_change(self, cursor: ResourceChangeCursor) -> str:
        return self._encode(
            (
                _CURSOR_VERSION,
                "rc",
                _datetime_value(cursor.resource_updated_at),
                str(cursor.resource_id),
            )
        )

    def decode_resource_change(
        self,
        token: str,
        *,
        kind: WhatsAppCursorKind,
    ) -> ResourceChangeCursor:
        values = self._decode(token, "rc", 4, kind)
        try:
            return ResourceChangeCursor(
                resource_updated_at=_datetime_from_value(values[2]),
                resource_id=_nonnegative_int(values[3]),
            )
        except ValueError as error:
            self._reject(kind, WhatsAppCursorRejectionReason.INVALID_VALUE, error)

    def _encode(self, values: tuple[str, ...]) -> str:
        payload = "|".join(values).encode()
        signature = digest(self._secret, payload, sha256)
        return f"{_urlsafe(payload)}.{_urlsafe(signature)}"

    def _decode(
        self,
        token: str,
        expected_kind: str,
        expected_parts: int,
        cursor_kind: WhatsAppCursorKind,
    ) -> tuple[str, ...]:
        try:
            payload_value, signature_value = token.split(".", maxsplit=1)
            payload = _urlsafe_decode(payload_value)
            signature = _urlsafe_decode(signature_value)
        except (UnicodeDecodeError, ValueError) as error:
            self._reject(
                cursor_kind,
                WhatsAppCursorRejectionReason.MALFORMED,
                error,
            )
        expected_signature = digest(self._secret, payload, sha256)
        if not compare_digest(signature, expected_signature):
            self._reject(
                cursor_kind,
                WhatsAppCursorRejectionReason.MALFORMED,
                ValueError("Invalid cursor signature"),
            )
        try:
            values = tuple(payload.decode().split("|"))
        except UnicodeDecodeError as error:
            self._reject(
                cursor_kind,
                WhatsAppCursorRejectionReason.MALFORMED,
                error,
            )
        if not values or values[0] != _CURSOR_VERSION:
            self._reject(
                cursor_kind,
                WhatsAppCursorRejectionReason.UNSUPPORTED_VERSION,
                ValueError("Unsupported cursor version"),
            )
        if len(values) != expected_parts or values[1] != expected_kind:
            self._reject(
                cursor_kind,
                WhatsAppCursorRejectionReason.INVALID_VALUE,
                ValueError("Cursor kind or field count is invalid"),
            )
        return values

    def _reject(
        self,
        kind: WhatsAppCursorKind,
        reason: WhatsAppCursorRejectionReason,
        error: Exception,
    ) -> Never:
        self._metrics.record_cursor_rejection(CursorRejectionMeasurement(kind, reason))
        raise InvalidWhatsAppCursorError("Invalid or unsupported cursor") from error


def _urlsafe(value: bytes) -> str:
    return urlsafe_b64encode(value).decode().rstrip("=")


def _urlsafe_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return urlsafe_b64decode(value + padding)


def _datetime_value(value: datetime) -> str:
    return _aware_utc(value).isoformat(timespec="microseconds")


def _datetime_from_value(value: str) -> datetime:
    return _aware_utc(datetime.fromisoformat(value))


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Cursor datetime must be timezone-aware")
    return value.astimezone(UTC)


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise ValueError("Cursor ID must be positive")
    return parsed


def _nonnegative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise ValueError("Cursor value cannot be negative")
    return parsed


def _bool_value(value: str) -> bool:
    if value == "1":
        return True
    if value == "0":
        return False
    raise ValueError("Cursor boolean is invalid")
