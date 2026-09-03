from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api import api_router
from app.api.error_handlers import domain_error_handler
from app.api.routers.whatsapp import create_whatsapp_router
from app.api.routers.whatsapp_broadcast import create_whatsapp_broadcast_router
from app.api.routers.whatsapp_dev import create_whatsapp_dev_router
from app.api.routers.whatsapp_provider_webhook import (
    create_whatsapp_provider_webhook_router,
)
from app.core.config import (
    RuntimeSecuritySettings,
    get_runtime_security_settings,
    get_stale_opportunity_days,
    validate_runtime_security_settings,
)
from app.core.security_middleware import (
    ProductionSecurityHeadersMiddleware,
    RequestBodyLimitMiddleware,
)
from app.db.session import engine
from app.services import DomainError
from app.whatsapp import (
    DisabledWhatsAppProvider,
    FakeMediaStorage,
    FakeWhatsAppProvider,
)
from app.whatsapp.runtime import (
    WhatsAppRuntime,
    build_configured_whatsapp_runtime,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    get_runtime_security_settings()
    get_stale_opportunity_days()
    yield
    engine.dispose()


def create_app(
    whatsapp_runtime: WhatsAppRuntime | None = None,
    *,
    security_settings: RuntimeSecuritySettings | None = None,
) -> FastAPI:
    settings = security_settings or get_runtime_security_settings()
    validate_runtime_security_settings(settings)
    runtime = whatsapp_runtime or build_configured_whatsapp_runtime()
    if settings.is_production and (
        isinstance(runtime.provider, FakeWhatsAppProvider)
        or isinstance(runtime.storage, FakeMediaStorage)
    ):
        raise RuntimeError(
            "Fake WhatsApp runtime components are not allowed in production"
        )
    application = FastAPI(
        title="Asfaltos CRM API",
        version="0.3.0",
        description=(
            "Authenticated REST API for FAA customers, products, users, and "
            "commercial opportunities."
        ),
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    application.state.runtime_security_settings = settings
    application.add_exception_handler(DomainError, domain_error_handler)
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=list(settings.allowed_hosts),
    )
    application.add_middleware(RequestBodyLimitMiddleware, settings.request_body_limits)
    if settings.is_production:
        application.add_middleware(ProductionSecurityHeadersMiddleware)
    application.include_router(api_router, prefix="/api")
    if not isinstance(runtime.provider, DisabledWhatsAppProvider):
        application.include_router(create_whatsapp_router(runtime), prefix="/api")
        application.include_router(
            create_whatsapp_broadcast_router(runtime),
            prefix="/api",
        )
        if settings.registers_whatsapp_dev_routes and isinstance(
            runtime.provider,
            FakeWhatsAppProvider,
        ):
            application.include_router(
                create_whatsapp_dev_router(runtime, runtime.provider),
                prefix="/api",
            )
        if runtime.webhook is not None:
            application.include_router(
                create_whatsapp_provider_webhook_router(runtime),
                prefix="/api",
            )
    return application


app = create_app()


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Checks that the API and its PostgreSQL connection are available."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable",
        ) from error

    return {"status": "ok", "database": "ok"}
