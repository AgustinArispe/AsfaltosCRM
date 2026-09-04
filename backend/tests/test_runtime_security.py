from dataclasses import replace
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import (
    REQUIRED_PRODUCTION_CORS_ORIGIN,
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
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", REQUIRED_PRODUCTION_CORS_ORIGIN)
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


@pytest.mark.parametrize(
    "origins",
    (
        "",
        "*",
        "https://*.railway.app",
        "http://robust-creativity-production-f6de.up.railway.app",
        "https://robust-creativity-production-f6de.up.railway.app/path",
        "https://another.example",
        f"{REQUIRED_PRODUCTION_CORS_ORIGIN},{REQUIRED_PRODUCTION_CORS_ORIGIN}",
        f"{REQUIRED_PRODUCTION_CORS_ORIGIN},https://another.example",
    ),
)
def test_production_rejects_unsafe_cors_origins(
    monkeypatch: pytest.MonkeyPatch,
    origins: str,
) -> None:
    _configure_production_environment(monkeypatch)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", origins)
    clear_runtime_settings_caches()

    with pytest.raises(RuntimeError, match="CORS_ALLOWED_ORIGINS"):
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


def test_cors_permits_allowed_origin_preflight_and_actual_request() -> None:
    application = _cors_application()

    with TestClient(application) as client:
        preflight = client.options(
            "/api/auth/login",
            headers={
                "Origin": REQUIRED_PRODUCTION_CORS_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,authorization",
            },
        )
        actual = client.post(
            "/api/auth/login",
            headers={"Origin": REQUIRED_PRODUCTION_CORS_ORIGIN},
            json={},
        )

    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == (
        REQUIRED_PRODUCTION_CORS_ORIGIN
    )
    assert "POST" in preflight.headers["access-control-allow-methods"]
    assert "content-type" in preflight.headers["access-control-allow-headers"].lower()
    assert "authorization" in preflight.headers["access-control-allow-headers"].lower()
    assert "access-control-allow-credentials" not in preflight.headers
    assert actual.status_code == 422
    assert (
        actual.headers["access-control-allow-origin"] == REQUIRED_PRODUCTION_CORS_ORIGIN
    )
    assert "access-control-allow-credentials" not in actual.headers


def test_cors_rejects_disallowed_origin_and_preserves_no_origin_requests() -> None:
    application = _cors_application()

    with TestClient(application) as client:
        preflight = client.options(
            "/api/auth/login",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "POST",
            },
        )
        disallowed_actual = client.post(
            "/api/auth/login",
            headers={"Origin": "https://untrusted.example"},
            json={},
        )
        no_origin = client.post("/api/auth/login", json={})

    assert preflight.status_code == 400
    assert "access-control-allow-origin" not in preflight.headers
    assert disallowed_actual.status_code == 422
    assert "access-control-allow-origin" not in disallowed_actual.headers
    assert no_origin.status_code == 422
    assert "access-control-allow-origin" not in no_origin.headers


def _has_whatsapp_dev_route(application: FastAPI) -> bool:
    return any(
        path.startswith("/api/whatsapp/dev/") for path in application.openapi()["paths"]
    )


def _cors_application() -> FastAPI:
    base = get_runtime_security_settings()
    settings = replace(
        base,
        environment=RuntimeEnvironment.TEST,
        cors_allowed_origins=(REQUIRED_PRODUCTION_CORS_ORIGIN,),
    )
    return create_app(build_fake_whatsapp_runtime(), security_settings=settings)
