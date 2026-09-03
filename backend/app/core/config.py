from dataclasses import dataclass, field
from enum import StrEnum
from functools import lru_cache
from os import getenv
from pathlib import Path
from typing import Final

from sqlalchemy.engine import make_url

JWT_ALGORITHM: Final = "HS256"
DEFAULT_ALLOWED_HOSTS: Final = ("localhost", "127.0.0.1", "backend", "testserver")
DEFAULT_WHATSAPP_IMAGE_MIME_TYPES: Final = (
    "image/jpeg",
    "image/png",
    "image/webp",
)
DEFAULT_WHATSAPP_DOCUMENT_MIME_TYPES: Final = ("application/pdf",)
DEFAULT_WHATSAPP_MEDIA_MAX_BYTES: Final = 16_777_216
DEFAULT_WHATSAPP_BROADCAST_BATCH_SIZE: Final = 10
MAX_WHATSAPP_BROADCAST_BATCH_SIZE: Final = 10
DEFAULT_WHATSAPP_BROADCAST_CLAIM_TIMEOUT_SECONDS: Final = 300
MAX_JWT_ACCESS_TOKEN_EXPIRE_MINUTES: Final = 60
WEB_INTAKE_BODY_MAX_BYTES: Final = 32 * 1024
META_WEBHOOK_BODY_MAX_BYTES: Final = 2 * 1024 * 1024
WHATSAPP_MEDIA_REQUEST_MAX_BYTES: Final = 17 * 1024 * 1024
CUSTOMER_IMPORT_REQUEST_MAX_BYTES: Final = 2_250_000
POSTGRESQL_URL_PREFIX: Final = "postgresql://"
PSYCOPG_POSTGRESQL_URL_PREFIX: Final = "postgresql+psycopg://"


class RuntimeEnvironment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


@dataclass(frozen=True, slots=True)
class RequestBodyLimits:
    web_intake_bytes: int = WEB_INTAKE_BODY_MAX_BYTES
    meta_webhook_bytes: int = META_WEBHOOK_BODY_MAX_BYTES
    whatsapp_media_bytes: int = WHATSAPP_MEDIA_REQUEST_MAX_BYTES
    customer_import_bytes: int = CUSTOMER_IMPORT_REQUEST_MAX_BYTES


@dataclass(frozen=True, slots=True)
class RuntimeSecuritySettings:
    environment: RuntimeEnvironment
    database_url: str = field(repr=False)
    jwt_secret: str = field(repr=False)
    web_intake_signing_secret: str = field(repr=False)
    jwt_access_token_expire_minutes: int = 60
    allowed_hosts: tuple[str, ...] = ()
    whatsapp_provider_name: str = "fake"
    whatsapp_media_storage_name: str = "fake"
    whatsapp_dev_routes_enabled: bool = False
    whatsapp_image_max_bytes: int = DEFAULT_WHATSAPP_MEDIA_MAX_BYTES
    whatsapp_document_max_bytes: int = DEFAULT_WHATSAPP_MEDIA_MAX_BYTES
    request_body_limits: RequestBodyLimits = RequestBodyLimits()

    @property
    def is_production(self) -> bool:
        return self.environment is RuntimeEnvironment.PRODUCTION

    @property
    def registers_whatsapp_dev_routes(self) -> bool:
        return (
            self.environment is RuntimeEnvironment.DEVELOPMENT
            and self.whatsapp_provider_name == "fake"
            and self.whatsapp_dev_routes_enabled
        )


@lru_cache
def get_app_environment() -> RuntimeEnvironment:
    raw_value = getenv("APP_ENVIRONMENT")
    if raw_value is None or not raw_value.strip():
        raise RuntimeError("APP_ENVIRONMENT environment variable is required")
    try:
        return RuntimeEnvironment(raw_value.strip().lower())
    except ValueError as error:
        raise RuntimeError(
            "APP_ENVIRONMENT must be 'development', 'test', or 'production'"
        ) from error


@lru_cache
def get_database_url() -> str:
    database_url = getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is required")
    return _normalize_database_url(database_url)


def _normalize_database_url(database_url: str) -> str:
    if database_url.startswith(POSTGRESQL_URL_PREFIX):
        return (
            f"{PSYCOPG_POSTGRESQL_URL_PREFIX}"
            f"{database_url.removeprefix(POSTGRESQL_URL_PREFIX)}"
        )
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
    if not 1 <= minutes <= MAX_JWT_ACCESS_TOKEN_EXPIRE_MINUTES:
        raise RuntimeError(
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be between 1 and "
            f"{MAX_JWT_ACCESS_TOKEN_EXPIRE_MINUTES}"
        )
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
def get_allowed_hosts() -> tuple[str, ...]:
    raw_value = getenv("ALLOWED_HOSTS", ",".join(DEFAULT_ALLOWED_HOSTS))
    allowed_hosts = tuple(host.strip() for host in raw_value.split(",") if host.strip())
    if not allowed_hosts:
        raise RuntimeError("ALLOWED_HOSTS must contain at least one host")
    if "*" in allowed_hosts:
        raise RuntimeError("ALLOWED_HOSTS cannot contain a wildcard")
    return allowed_hosts


@lru_cache
def get_whatsapp_provider_name() -> str:
    provider_name = getenv("WHATSAPP_PROVIDER", "fake").strip().lower()
    if provider_name not in {"fake", "meta"}:
        raise RuntimeError("WHATSAPP_PROVIDER must be 'fake' or 'meta'")
    return provider_name


@lru_cache
def get_whatsapp_dev_routes_enabled() -> bool:
    raw_value = getenv("WHATSAPP_DEV_ROUTES_ENABLED", "false").strip().lower()
    if raw_value == "true":
        return True
    if raw_value == "false":
        return False
    raise RuntimeError("WHATSAPP_DEV_ROUTES_ENABLED must be 'true' or 'false'")


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
def get_whatsapp_broadcast_batch_size() -> int:
    batch_size = _positive_int_setting(
        "WHATSAPP_BROADCAST_BATCH_SIZE",
        str(DEFAULT_WHATSAPP_BROADCAST_BATCH_SIZE),
    )
    if batch_size > MAX_WHATSAPP_BROADCAST_BATCH_SIZE:
        raise RuntimeError(
            "WHATSAPP_BROADCAST_BATCH_SIZE must be no greater than "
            f"{MAX_WHATSAPP_BROADCAST_BATCH_SIZE}"
        )
    return batch_size


@lru_cache
def get_whatsapp_broadcast_claim_timeout_seconds() -> int:
    return _positive_int_setting(
        "WHATSAPP_BROADCAST_CLAIM_TIMEOUT_SECONDS",
        str(DEFAULT_WHATSAPP_BROADCAST_CLAIM_TIMEOUT_SECONDS),
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


@lru_cache
def get_runtime_security_settings() -> RuntimeSecuritySettings:
    settings = RuntimeSecuritySettings(
        environment=get_app_environment(),
        database_url=get_database_url(),
        jwt_secret=get_jwt_secret(),
        web_intake_signing_secret=get_web_intake_signing_secret(),
        jwt_access_token_expire_minutes=get_access_token_expire_minutes(),
        allowed_hosts=get_allowed_hosts(),
        whatsapp_provider_name=get_whatsapp_provider_name(),
        whatsapp_media_storage_name=get_whatsapp_media_storage_name(),
        whatsapp_dev_routes_enabled=get_whatsapp_dev_routes_enabled(),
        whatsapp_image_max_bytes=get_whatsapp_image_max_bytes(),
        whatsapp_document_max_bytes=get_whatsapp_document_max_bytes(),
    )
    validate_runtime_security_settings(settings)
    return settings


def clear_runtime_settings_caches() -> None:
    get_app_environment.cache_clear()
    get_database_url.cache_clear()
    get_jwt_secret.cache_clear()
    get_web_intake_signing_secret.cache_clear()
    get_access_token_expire_minutes.cache_clear()
    get_allowed_hosts.cache_clear()
    get_whatsapp_provider_name.cache_clear()
    get_whatsapp_dev_routes_enabled.cache_clear()
    get_whatsapp_image_max_bytes.cache_clear()
    get_whatsapp_document_max_bytes.cache_clear()
    get_whatsapp_media_storage_name.cache_clear()
    get_runtime_security_settings.cache_clear()


def validate_runtime_security_settings(settings: RuntimeSecuritySettings) -> None:
    if not settings.is_production:
        return
    if settings.whatsapp_provider_name != "meta":
        raise RuntimeError("WHATSAPP_PROVIDER must be 'meta' in production")
    if settings.whatsapp_media_storage_name != "filesystem":
        raise RuntimeError("WHATSAPP_MEDIA_STORAGE must be 'filesystem' in production")
    if settings.whatsapp_dev_routes_enabled:
        raise RuntimeError("WHATSAPP_DEV_ROUTES_ENABLED cannot be true in production")
    if settings.jwt_secret == settings.web_intake_signing_secret:
        raise RuntimeError("JWT_SECRET and WEB_INTAKE_SIGNING_SECRET must differ")
    _require_production_secret("JWT_SECRET", settings.jwt_secret)
    _require_production_secret(
        "WEB_INTAKE_SIGNING_SECRET",
        settings.web_intake_signing_secret,
    )
    for host in settings.allowed_hosts:
        if not _is_valid_production_host(host):
            raise RuntimeError("ALLOWED_HOSTS contains an unsafe production host")
    _validate_production_database_url(settings.database_url)
    if (
        settings.whatsapp_image_max_bytes > DEFAULT_WHATSAPP_MEDIA_MAX_BYTES
        or settings.whatsapp_document_max_bytes > DEFAULT_WHATSAPP_MEDIA_MAX_BYTES
    ):
        raise RuntimeError("WhatsApp media limits cannot exceed 16 MiB in production")
    # MetaConfig owns its integration-specific typed validation.  Calling it here
    # keeps production provider validation inside the one startup policy rather
    # than allowing router assembly to discover missing credentials later.
    from app.whatsapp.meta_config import MetaConfig

    MetaConfig.from_environment()


def _require_production_secret(name: str, value: str) -> None:
    unsafe_markers = (
        "replace",
        "placeholder",
        "change_me",
        "default",
        "example",
        "test",
        "ci-",
        "local",
    )
    normalized = value.strip().lower()
    if any(marker in normalized for marker in unsafe_markers):
        raise RuntimeError(f"{name} contains an unsafe placeholder or default")


def _is_valid_production_host(host: str) -> bool:
    normalized = host.strip().lower()
    blocked_hosts = {"localhost", "testserver", "backend", "db", "0.0.0.0", "::1"}
    if (
        not normalized
        or normalized in blocked_hosts
        or normalized.startswith("127.")
        or normalized.endswith(".local")
        or ":" in normalized
        or "/" in normalized
        or "@" in normalized
        or normalized.startswith(".")
    ):
        return False
    labels = normalized.split(".")
    return len(labels) >= 2 and all(
        label
        and len(label) <= 63
        and label[0].isalnum()
        and label[-1].isalnum()
        and all(character.isalnum() or character == "-" for character in label)
        for label in labels
    )


def _validate_production_database_url(database_url: str) -> None:
    try:
        url = make_url(database_url)
    except Exception as error:
        raise RuntimeError("DATABASE_URL is invalid for production") from error
    if url.drivername != "postgresql+psycopg" or not url.password:
        raise RuntimeError("DATABASE_URL must use PostgreSQL password authentication")
    _require_production_secret("DATABASE_URL password", url.password)


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
