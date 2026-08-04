from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api import api_router
from app.api.error_handlers import domain_error_handler
from app.db.session import engine
from app.services import DomainError


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    engine.dispose()


app = FastAPI(
    title="Asfaltos CRM API",
    version="0.2.0",
    description="REST API for FAA customers, products, and commercial opportunities.",
    lifespan=lifespan,
)
app.add_exception_handler(DomainError, domain_error_handler)
app.include_router(api_router, prefix="/api")


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
