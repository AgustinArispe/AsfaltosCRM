from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Protocol, cast
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.db.session import engine


class Migration(Protocol):
    def upgrade(self) -> None: ...
    def downgrade(self) -> None: ...


def test_follow_up_migration_preserves_existing_data_and_guards_recorded_follow_ups() -> (
    None
):
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic/versions/0020_opportunity_follow_up.py"
    )
    specification = spec_from_file_location("crm060_migration", path)
    assert specification is not None and specification.loader is not None
    module = module_from_spec(specification)
    specification.loader.exec_module(module)
    migration = cast(Migration, module)
    schema = f"crm060_migration_{uuid4().hex}"
    with engine.connect() as connection:
        try:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(text(f'SET search_path TO "{schema}"'))
            connection.execute(text("CREATE TABLE users (id BIGINT PRIMARY KEY)"))
            connection.execute(text("INSERT INTO users VALUES (1)"))
            connection.execute(
                text(
                    "CREATE TABLE opportunities (id BIGINT PRIMARY KEY, created_at TIMESTAMPTZ NOT NULL)"
                )
            )
            connection.execute(
                text("INSERT INTO opportunities VALUES (1,'2026-01-01T00:00:00Z')")
            )
            connection.commit()
            context = MigrationContext.configure(connection)
            with context.begin_transaction(), Operations.context(context):
                migration.upgrade()
            assert connection.execute(
                text(
                    "SELECT last_followed_up_at, last_followed_up_by_user_id FROM opportunities"
                )
            ).one() == (None, None)
            connection.commit()
            for assignment in (
                "last_followed_up_by_user_id=1",
                "last_followed_up_at='2026-02-01T00:00:00Z'",
                "last_followed_up_at='2025-01-01T00:00:00Z', last_followed_up_by_user_id=1",
                "last_followed_up_at='2026-02-01T00:00:00Z', last_followed_up_by_user_id=999",
            ):
                with pytest.raises(DBAPIError), connection.begin():
                    connection.execute(text(f"UPDATE opportunities SET {assignment}"))
            connection.execute(
                text(
                    "UPDATE opportunities SET last_followed_up_at='2026-02-01T00:00:00Z', last_followed_up_by_user_id=1"
                )
            )
            connection.commit()
            with (
                Operations.context(context),
                pytest.raises(RuntimeError, match="reviewed backup"),
            ):
                migration.downgrade()
            assert (
                connection.scalar(
                    text("SELECT last_followed_up_by_user_id FROM opportunities")
                )
                == 1
            )
        finally:
            connection.rollback()
            connection.execute(text("SET search_path TO public"))
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            connection.commit()
