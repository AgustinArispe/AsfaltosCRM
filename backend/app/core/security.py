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
    expires_delta: timedelta | None = None,
    now: datetime | None = None,
) -> str:
    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=get_access_token_expire_minutes())
    )
    return jwt.encode(
        {"sub": str(user_id), "iat": issued_at, "exp": expires_at},
        get_jwt_secret(),
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> int:
    payload = jwt.decode(
        token,
        get_jwt_secret(),
        algorithms=[JWT_ALGORITHM],
        options={"require": ["sub", "exp"]},
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
    return user_id
