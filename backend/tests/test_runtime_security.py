from dataclasses import replace
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import (
    RuntimeEnvironment,
    clear_runtime_settings_caches,
    get_runtime_security_settings,
)
from app.main import create_app
from app.whatsapp import DisabledWhatsAppProvider, FilesystemMediaStorage, MetaConfig
from app.whatsapp.runtime import (
    build_configured_whatsapp_runtime,
    build_fake_whatsapp_runtime,
    build_meta_whatsapp_runtime,
)


def _configure_production_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENVIRONMENT", "production")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://faa:ProductionDatabasePassword90210@db.faa.example/crm",
    )
    monkeypatch.setenv("JWT_SECRET", "JwtSecretForProductionOnly1234567890")
    monkeypatch.setenv(
        "WEB_INTAKE_SIGNING_SECRET",
        "IntakeSecretForProductionOnly1234567890",
    )
    monkeypatch.setenv("ALLOWED_HOSTS", "crm.faa.example")
    monkeypatch.setenv("WHATSAPP_PROVIDER", "meta")
    monkeypatch.setenv("WHATSAPP_MEDIA_STORAGE", "filesystem")
    monkeypatch.setenv("WHATSAPP_DEV_ROUTES_ENABLED", "false")
    monkeypatch.setenv("META_GRAPH_API_VERSION", "v26.0")
    monkeypatch.setenv("META_ACCESS_TOKEN", "meta-access-token-production-value")
    monkeypatch.setenv("META_PHONE_NUMBER_ID", "106540352242922")
    monkeypatch.setenv("META_WABA_ID", "102290129340398")
    monkeypatch.setenv("META_WEBHOOK_VERIFY_TOKEN", "meta-webhook-verify-production")
    monkeypatch.setenv("META_APP_SECRET", "meta-app-secret-production-value")


def test_production_runtime_configuration_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_production_environment(monkeypatch)
    monkeypatch.setenv("ALLOWED_HOSTS", "*")
    clear_runtime_settings_caches()

    with pytest.raises(RuntimeError, match="ALLOWED_HOSTS"):
        get_runtime_security_settings()

    monkeypatch.setenv("ALLOWED_HOSTS", "crm.faa.example")
    monkeypatch.setenv("JWT_SECRET", "replace-this-production-secret-123456")
    clear_runtime_settings_caches()
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        get_runtime_security_settings()
    clear_runtime_settings_caches()


def test_production_rejects_fake_whatsapp_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_production_environment(monkeypatch)
    monkeypatch.setenv("WHATSAPP_PROVIDER", "fake")
    clear_runtime_settings_caches()

    with pytest.raises(RuntimeError, match="WHATSAPP_PROVIDER"):
        get_runtime_security_settings()

    clear_runtime_settings_caches()


def test_production_disabled_whatsapp_omits_whatsapp_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_production_environment(monkeypatch)
    monkeypatch.setenv("WHATSAPP_PROVIDER", "disabled")
    for name in (
        "META_GRAPH_API_VERSION",
        "META_ACCESS_TOKEN",
        "META_PHONE_NUMBER_ID",
        "META_WABA_ID",
        "META_WEBHOOK_VERIFY_TOKEN",
        "META_APP_SECRET",
    ):
        monkeypatch.delenv(name)
    clear_runtime_settings_caches()

    settings = get_runtime_security_settings()
    runtime = build_configured_whatsapp_runtime()
    application = create_app(runtime, security_settings=settings)
    paths = application.openapi()["paths"]

    assert isinstance(runtime.provider, DisabledWhatsAppProvider)
    assert isinstance(runtime.storage, FilesystemMediaStorage)
    assert runtime.webhook is None
    assert "/api/customers" in paths
    assert not any(path.startswith("/api/whatsapp") for path in paths)

    clear_runtime_settings_caches()


def test_production_meta_provider_still_requires_meta_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_production_environment(monkeypatch)
    monkeypatch.delenv("META_ACCESS_TOKEN")
    clear_runtime_settings_caches()

    with pytest.raises(RuntimeError, match="META_ACCESS_TOKEN"):
        get_runtime_security_settings()

    clear_runtime_settings_caches()


def test_whatsapp_development_routes_require_explicit_development_double_opt_in() -> (
    None
):
    base = get_runtime_security_settings()
    runtime = build_fake_whatsapp_runtime()
    test_application = create_app(
        runtime,
        security_settings=replace(
            base,
            environment=RuntimeEnvironment.TEST,
            whatsapp_provider_name="fake",
            whatsapp_dev_routes_enabled=True,
        ),
    )
    development_without_flag = create_app(
        runtime,
        security_settings=replace(
            base,
            environment=RuntimeEnvironment.DEVELOPMENT,
            whatsapp_provider_name="fake",
            whatsapp_dev_routes_enabled=False,
        ),
    )
    development_application = create_app(
        runtime,
        security_settings=replace(
            base,
            environment=RuntimeEnvironment.DEVELOPMENT,
            whatsapp_provider_name="fake",
            whatsapp_dev_routes_enabled=True,
        ),
    )

    assert not _has_whatsapp_dev_route(test_application)
    assert not _has_whatsapp_dev_route(development_without_flag)
    assert _has_whatsapp_dev_route(development_application)

    with pytest.raises(RuntimeError, match="WHATSAPP_PROVIDER"):
        create_app(
            runtime,
            security_settings=replace(
                base,
                environment=RuntimeEnvironment.PRODUCTION,
                whatsapp_provider_name="fake",
            ),
        )


def test_production_hides_api_documentation_and_sets_security_headers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_production_environment(monkeypatch)
    clear_runtime_settings_caches()
    settings = get_runtime_security_settings()
    config = MetaConfig.from_environment()
    runtime = build_meta_whatsapp_runtime(
        config=config,
        storage=FilesystemMediaStorage(tmp_path),
    )
    application = create_app(runtime, security_settings=settings)

    with TestClient(application) as client:
        for path in ("/docs", "/redoc", "/openapi.json"):
            response = client.get(path, headers={"Host": "crm.faa.example"})
            assert response.status_code == 404
            assert response.headers["strict-transport-security"] == "max-age=31536000"
            assert response.headers["x-content-type-options"] == "nosniff"
            assert (
                "frame-ancestors 'none'" in response.headers["content-security-policy"]
            )
            assert response.headers["x-frame-options"] == "DENY"
            assert response.headers["referrer-policy"] == "no-referrer"
            assert "camera=()" in response.headers["permissions-policy"]
    clear_runtime_settings_caches()


def _has_whatsapp_dev_route(application: FastAPI) -> bool:
    return any(
        path.startswith("/api/whatsapp/dev/") for path in application.openapi()["paths"]
    )
