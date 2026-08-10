from __future__ import annotations

from dataclasses import dataclass, field
from os import getenv
from re import fullmatch


@dataclass(frozen=True, slots=True)
class MetaConfig:
    graph_api_version: str
    access_token: str = field(repr=False)
    phone_number_id: str
    waba_id: str
    webhook_verify_token: str = field(repr=False)
    app_secret: str = field(repr=False)
    request_timeout_seconds: float
    retry_max_attempts: int
    retry_base_seconds: float
    retry_max_seconds: float

    @classmethod
    def from_environment(cls) -> MetaConfig:
        config = cls(
            graph_api_version=_required("META_GRAPH_API_VERSION"),
            access_token=_required("META_ACCESS_TOKEN"),
            phone_number_id=_required("META_PHONE_NUMBER_ID"),
            waba_id=_required("META_WABA_ID"),
            webhook_verify_token=_required("META_WEBHOOK_VERIFY_TOKEN"),
            app_secret=_required("META_APP_SECRET"),
            request_timeout_seconds=_float_setting(
                "META_REQUEST_TIMEOUT_SECONDS",
                default="10",
            ),
            retry_max_attempts=_int_setting(
                "META_RETRY_MAX_ATTEMPTS",
                default="3",
            ),
            retry_base_seconds=_float_setting(
                "META_RETRY_BASE_SECONDS",
                default="0.25",
            ),
            retry_max_seconds=_float_setting(
                "META_RETRY_MAX_SECONDS",
                default="2",
            ),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if fullmatch(r"v[0-9]+\.[0-9]+", self.graph_api_version) is None:
            raise RuntimeError("META_GRAPH_API_VERSION is invalid")
        if not self.phone_number_id.isdecimal():
            raise RuntimeError("META_PHONE_NUMBER_ID must be numeric")
        if not self.waba_id.isdecimal():
            raise RuntimeError("META_WABA_ID must be numeric")
        if not 1.0 <= self.request_timeout_seconds <= 120.0:
            raise RuntimeError("META_REQUEST_TIMEOUT_SECONDS must be between 1 and 120")
        if not 1 <= self.retry_max_attempts <= 10:
            raise RuntimeError("META_RETRY_MAX_ATTEMPTS must be between 1 and 10")
        if not 0.0 < self.retry_base_seconds <= 60.0:
            raise RuntimeError("META_RETRY_BASE_SECONDS must be between 0 and 60")
        if not self.retry_base_seconds <= self.retry_max_seconds <= 300.0:
            raise RuntimeError(
                "META_RETRY_MAX_SECONDS must be at least the base and at most 300"
            )


def _required(name: str) -> str:
    value = getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"{name} environment variable is required in Meta mode")
    return value.strip()


def _float_setting(name: str, *, default: str) -> float:
    raw_value = getenv(name, default)
    try:
        return float(raw_value)
    except ValueError as error:
        raise RuntimeError(f"{name} must be numeric") from error


def _int_setting(name: str, *, default: str) -> int:
    raw_value = getenv(name, default)
    try:
        return int(raw_value)
    except ValueError as error:
        raise RuntimeError(f"{name} must be an integer") from error
