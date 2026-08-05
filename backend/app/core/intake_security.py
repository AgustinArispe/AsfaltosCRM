import hmac
from datetime import UTC, datetime
from hashlib import sha256

from app.core.config import get_web_intake_signing_secret
from app.services.errors import IntakeAuthenticationError

WEB_INTAKE_METHOD = "POST"
WEB_INTAKE_PATH = "/api/intake/web"
WEB_INTAKE_SIGNATURE_MAX_AGE_SECONDS = 300
_SIGNATURE_PREFIX = "sha256="


def build_web_intake_signature(
    timestamp: str,
    raw_body: bytes,
    *,
    secret: str | None = None,
) -> str:
    """Build the canonical signature used by trusted server integrations."""
    signing_secret = secret or get_web_intake_signing_secret()
    signed_payload = (
        f"{timestamp}\n{WEB_INTAKE_METHOD}\n{WEB_INTAKE_PATH}\n".encode() + raw_body
    )
    digest = hmac.new(
        signing_secret.encode(),
        signed_payload,
        sha256,
    ).hexdigest()
    return f"{_SIGNATURE_PREFIX}{digest}"


def verify_web_intake_signature(
    timestamp: str | None,
    signature: str | None,
    raw_body: bytes,
    *,
    now: datetime | None = None,
) -> None:
    authentication_error = IntakeAuthenticationError(
        "Could not authenticate intake request"
    )
    if timestamp is None or signature is None:
        raise authentication_error
    try:
        timestamp_seconds = int(timestamp)
    except ValueError as error:
        raise authentication_error from error

    current_time = now or datetime.now(UTC)
    try:
        signature_age = abs(current_time.timestamp() - timestamp_seconds)
    except OverflowError as error:
        raise authentication_error from error
    if signature_age > WEB_INTAKE_SIGNATURE_MAX_AGE_SECONDS:
        raise authentication_error

    expected = build_web_intake_signature(timestamp, raw_body)
    if not hmac.compare_digest(signature, expected):
        raise authentication_error
