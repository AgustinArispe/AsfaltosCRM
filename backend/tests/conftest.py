from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.db.session import engine
from app.main import app


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
def api_client(db_session: Session) -> Iterator[TestClient]:
    def override_db_session() -> Iterator[Session]:
        try:
            yield db_session
        finally:
            if db_session.in_transaction():
                db_session.rollback()

    app.dependency_overrides[get_db_session] = override_db_session
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
