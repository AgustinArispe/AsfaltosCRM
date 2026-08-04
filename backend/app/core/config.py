from functools import lru_cache
from os import getenv


JWT_ALGORITHM = "HS256"


@lru_cache
def get_database_url() -> str:
    database_url = getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is required")
    return database_url


@lru_cache
def get_jwt_secret() -> str:
    jwt_secret = getenv("JWT_SECRET")
    if not jwt_secret:
        raise RuntimeError("JWT_SECRET environment variable is required")
    if len(jwt_secret) < 32:
        raise RuntimeError("JWT_SECRET must contain at least 32 characters")
    return jwt_secret


@lru_cache
def get_access_token_expire_minutes() -> int:
    raw_value = getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    try:
        minutes = int(raw_value)
    except ValueError as error:
        raise RuntimeError(
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be an integer"
        ) from error
    if minutes <= 0:
        raise RuntimeError(
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be greater than zero"
        )
    return minutes
