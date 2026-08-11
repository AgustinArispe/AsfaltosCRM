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
    get_allowed_hosts,
    get_jwt_secret,
    get_stale_opportunity_days,
    get_web_intake_signing_secret,
)
from app.db.session import engine
from app.services import DomainError
from app.whatsapp import FakeWhatsAppProvider
from app.whatsapp.runtime import (
    WhatsAppRuntime,
    build_configured_whatsapp_runtime,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    get_jwt_secret()
    get_web_intake_signing_secret()
    get_stale_opportunity_days()
    yield
    engine.dispose()


def create_app(whatsapp_runtime: WhatsAppRuntime | None = None) -> FastAPI:
    runtime = whatsapp_runtime or build_configured_whatsapp_runtime()
    application = FastAPI(
        title="Asfaltos CRM API",
        version="0.3.0",
        description=(
            "Authenticated REST API for FAA customers, products, users, and "
            "commercial opportunities."
        ),
        lifespan=lifespan,
    )
    application.add_exception_handler(DomainError, domain_error_handler)
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=get_allowed_hosts(),
    )
    application.include_router(api_router, prefix="/api")
    application.include_router(create_whatsapp_router(runtime), prefix="/api")
    application.include_router(
        create_whatsapp_broadcast_router(runtime),
        prefix="/api",
    )
    if isinstance(runtime.provider, FakeWhatsAppProvider):
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
