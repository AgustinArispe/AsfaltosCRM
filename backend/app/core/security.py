from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from app.core.config import (
    JWT_ALGORITHM,
    get_access_token_expire_minutes,
    get_jwt_secret,
)

_password_hash = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = _password_hash.hash("not-a-real-user-password")
JWT_CLOCK_SKEW_SECONDS = 30


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    user_id: int
    auth_session_version: int


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hash.verify(password, password_hash)
    except (UnknownHashError, ValueError):
        return False


def create_access_token(
    user_id: int,
    *,
    auth_session_version: int = 1,
    expires_delta: timedelta | None = None,
    now: datetime | None = None,
) -> str:
    if user_id <= 0:
        raise ValueError("Token user ID must be positive")
    if isinstance(auth_session_version, bool) or auth_session_version <= 0:
        raise ValueError("Token auth session version must be positive")
    issued_at = now or datetime.now(UTC)
    if issued_at.tzinfo is None:
        raise ValueError("Token issue time must be timezone-aware")
    expires_at = issued_at + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=get_access_token_expire_minutes())
    )
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": issued_at,
            "exp": expires_at,
            "ver": auth_session_version,
        },
        get_jwt_secret(),
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(
    token: str,
    *,
    now: datetime | None = None,
) -> AccessTokenClaims:
    payload = jwt.decode(
        token,
        get_jwt_secret(),
        algorithms=[JWT_ALGORITHM],
        options={"require": ["sub", "exp", "iat", "ver"]},
        leeway=JWT_CLOCK_SKEW_SECONDS,
    )
    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise InvalidTokenError("Token subject must be a user id")
    try:
        user_id = int(subject)
    except (TypeError, ValueError) as error:
        raise InvalidTokenError("Token subject must be a user id") from error
    if user_id <= 0:
        raise InvalidTokenError("Token subject must be a positive user id")
    auth_session_version = payload.get("ver")
    if (
        isinstance(auth_session_version, bool)
        or not isinstance(auth_session_version, int)
        or auth_session_version <= 0
    ):
        raise InvalidTokenError("Token auth session version is invalid")
    issued_at_seconds = _numeric_date(payload.get("iat"), "issue time")
    expires_at_seconds = _numeric_date(payload.get("exp"), "expiration")
    current_time = now or datetime.now(UTC)
    if current_time.tzinfo is None:
        raise ValueError("Token validation time must be timezone-aware")
    current_seconds = current_time.timestamp()
    if issued_at_seconds > current_seconds + JWT_CLOCK_SKEW_SECONDS:
        raise InvalidTokenError("Token issue time is in the future")
    if expires_at_seconds <= issued_at_seconds:
        raise InvalidTokenError("Token expiration must follow issue time")
    maximum_lifetime_seconds = get_access_token_expire_minutes() * 60
    if (
        expires_at_seconds - issued_at_seconds
        > maximum_lifetime_seconds + JWT_CLOCK_SKEW_SECONDS
    ):
        raise InvalidTokenError("Token expiration exceeds the configured lifetime")
    return AccessTokenClaims(
        user_id=user_id,
        auth_session_version=auth_session_version,
    )


def _numeric_date(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise InvalidTokenError(f"Token {label} is invalid")
    return float(value)
