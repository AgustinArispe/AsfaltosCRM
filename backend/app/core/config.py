from functools import lru_cache
from os import getenv
from pathlib import Path

JWT_ALGORITHM = "HS256"
DEFAULT_ALLOWED_HOSTS = ("localhost", "127.0.0.1", "backend", "testserver")
DEFAULT_WHATSAPP_IMAGE_MIME_TYPES = (
    "image/jpeg",
    "image/png",
    "image/webp",
)
DEFAULT_WHATSAPP_DOCUMENT_MIME_TYPES = ("application/pdf",)
DEFAULT_WHATSAPP_MEDIA_MAX_BYTES = 16_777_216


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
def get_web_intake_signing_secret() -> str:
    signing_secret = getenv("WEB_INTAKE_SIGNING_SECRET")
    if not signing_secret:
        raise RuntimeError("WEB_INTAKE_SIGNING_SECRET environment variable is required")
    if len(signing_secret) < 32:
        raise RuntimeError(
            "WEB_INTAKE_SIGNING_SECRET must contain at least 32 characters"
        )
    return signing_secret


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
        raise RuntimeError("JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be greater than zero")
    return minutes


@lru_cache
def get_stale_opportunity_days() -> int:
    raw_value = getenv("STALE_OPPORTUNITY_DAYS", "14")
    try:
        days = int(raw_value)
    except ValueError as error:
        raise RuntimeError("STALE_OPPORTUNITY_DAYS must be an integer") from error
    if days <= 0:
        raise RuntimeError("STALE_OPPORTUNITY_DAYS must be greater than zero")
    return days


@lru_cache
def get_allowed_hosts() -> list[str]:
    raw_value = getenv("ALLOWED_HOSTS", ",".join(DEFAULT_ALLOWED_HOSTS))
    allowed_hosts = [host.strip() for host in raw_value.split(",") if host.strip()]
    if not allowed_hosts:
        raise RuntimeError("ALLOWED_HOSTS must contain at least one host")
    if "*" in allowed_hosts:
        raise RuntimeError("ALLOWED_HOSTS cannot contain a wildcard")
    return allowed_hosts


@lru_cache
def get_whatsapp_provider_name() -> str:
    provider_name = getenv("WHATSAPP_PROVIDER", "fake").strip().lower()
    if provider_name != "fake":
        raise RuntimeError(
            "WHATSAPP_PROVIDER must be 'fake' until another adapter is implemented"
        )
    return provider_name


@lru_cache
def get_whatsapp_image_max_bytes() -> int:
    return _positive_int_setting(
        "WHATSAPP_IMAGE_MAX_BYTES",
        getenv("WHATSAPP_MEDIA_MAX_BYTES", str(DEFAULT_WHATSAPP_MEDIA_MAX_BYTES)),
    )


@lru_cache
def get_whatsapp_document_max_bytes() -> int:
    return _positive_int_setting(
        "WHATSAPP_DOCUMENT_MAX_BYTES",
        getenv("WHATSAPP_MEDIA_MAX_BYTES", str(DEFAULT_WHATSAPP_MEDIA_MAX_BYTES)),
    )


@lru_cache
def get_whatsapp_media_storage_name() -> str:
    storage_name = getenv("WHATSAPP_MEDIA_STORAGE", "fake").strip().lower()
    if storage_name not in {"fake", "filesystem"}:
        raise RuntimeError("WHATSAPP_MEDIA_STORAGE must be 'fake' or 'filesystem'")
    return storage_name


@lru_cache
def get_whatsapp_media_storage_root() -> Path:
    raw_value = getenv(
        "WHATSAPP_MEDIA_STORAGE_ROOT",
        "/var/lib/asfaltos-crm/whatsapp-media",
    ).strip()
    if not raw_value:
        raise RuntimeError("WHATSAPP_MEDIA_STORAGE_ROOT cannot be empty")
    return Path(raw_value)


def _positive_int_setting(name: str, default: str) -> int:
    raw_value = getenv(name, default)
    try:
        maximum = int(raw_value)
    except ValueError as error:
        raise RuntimeError(f"{name} must be an integer") from error
    if maximum <= 0:
        raise RuntimeError(f"{name} must be greater than zero")
    return maximum


@lru_cache
def get_whatsapp_image_mime_types() -> frozenset[str]:
    return _mime_type_setting(
        "WHATSAPP_IMAGE_MIME_TYPES",
        DEFAULT_WHATSAPP_IMAGE_MIME_TYPES,
    )


@lru_cache
def get_whatsapp_document_mime_types() -> frozenset[str]:
    return _mime_type_setting(
        "WHATSAPP_DOCUMENT_MIME_TYPES",
        DEFAULT_WHATSAPP_DOCUMENT_MIME_TYPES,
    )


def _mime_type_setting(
    name: str,
    default: tuple[str, ...],
) -> frozenset[str]:
    raw_value = getenv(name, ",".join(default))
    values = frozenset(
        value.strip().lower() for value in raw_value.split(",") if value.strip()
    )
    if not values:
        raise RuntimeError(f"{name} must contain at least one MIME type")
    return values
