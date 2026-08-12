from collections.abc import Iterator
from dataclasses import replace
from os import environ

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

environ.setdefault("APP_ENVIRONMENT", "test")

from app.api.dependencies import get_db_session
from app.core.config import (
    RuntimeEnvironment,
    RuntimeSecuritySettings,
    get_runtime_security_settings,
)
from app.core.security import create_access_token, hash_password
from app.db.session import engine
from app.main import app
from app.models import User, UserRole

TEST_SUPERVISOR_PASSWORD = "supervisor-test-password"


def development_security_settings() -> RuntimeSecuritySettings:
    return replace(
        get_runtime_security_settings(),
        environment=RuntimeEnvironment.DEVELOPMENT,
        whatsapp_provider_name="fake",
        whatsapp_media_storage_name="fake",
        whatsapp_dev_routes_enabled=True,
    )


@pytest.fixture
def db_session() -> Iterator[Session]:
    """Runs each persistence test inside an isolated PostgreSQL transaction."""
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(
            bind=connection,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )

        try:
            yield session
        finally:
            session.close()
            transaction.rollback()


@pytest.fixture
def supervisor_user(db_session: Session) -> User:
    user = User(
        full_name="Supervisor de tests",
        email="supervisor-tests@faa.test",
        password_hash=hash_password(TEST_SUPERVISOR_PASSWORD),
        role=UserRole.SUPERVISOR,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def api_client(
    db_session: Session,
    supervisor_user: User,
) -> Iterator[TestClient]:
    def override_db_session() -> Iterator[Session]:
        try:
            yield db_session
        finally:
            if db_session.in_transaction():
                db_session.commit()

    app.dependency_overrides[get_db_session] = override_db_session
    try:
        with TestClient(app) as client:
            client.headers["Authorization"] = (
                f"Bearer {create_access_token(supervisor_user.id)}"
            )
            yield client
    finally:
        app.dependency_overrides.clear()
