from collections.abc import Callable
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Protocol, cast
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError

from app.db.session import engine

_LEGACY_OTHER_DETAIL = "Detalle no registrado (pérdida anterior)"
_MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "0012_other_loss_reason_detail.py"
)


class _MigrationContract(Protocol):
    def upgrade(self) -> None: ...

    def downgrade(self) -> None: ...


def test_0012_backfills_legacy_other_loss_events_and_restores_append_only_trigger() -> (
    None
):
    """CRM-046 AC-07: migrate legacy OTRO evidence without relaxing append-only history."""
    migration = _load_migration()
    schema = f"migration_0012_{uuid4().hex}"
    with engine.begin() as connection:
        _create_0011_legacy_schema(connection, schema)

        _run_migration(connection, schema, migration.upgrade)
        assert _loss_reason_detail(connection) == _LEGACY_OTHER_DETAIL
        assert _trigger_is_enabled(connection) is True
        _assert_loss_event_remains_append_only(connection)

        _run_migration(connection, schema, migration.downgrade)
        assert _column_exists(connection, "opportunity_loss_events") is False
        assert _trigger_is_enabled(connection) is True

        _run_migration(connection, schema, migration.upgrade)
        assert _loss_reason_detail(connection) == _LEGACY_OTHER_DETAIL
        assert _trigger_is_enabled(connection) is True
        _assert_loss_event_remains_append_only(connection)


def _create_0011_legacy_schema(connection: Connection, schema: str) -> None:
    connection.execute(text(f"CREATE SCHEMA {schema}"))
    connection.execute(text(f"SET LOCAL search_path TO {schema}, public"))
    connection.execute(
        text(
            "CREATE TABLE opportunities (id BIGINT PRIMARY KEY, loss_reason TEXT NULL)"
        )
    )

    connection.execute(
        text(
            "CREATE TABLE opportunity_loss_events ("
            "id BIGINT PRIMARY KEY, reason TEXT NOT NULL, "
            "customer_display_name TEXT NOT NULL)"
        )
    )
    connection.execute(
        text("INSERT INTO opportunities (id, loss_reason) VALUES (1, 'OTRO')")
    )
    connection.execute(
        text(
            "INSERT INTO opportunity_loss_events (id, reason, customer_display_name) "
            "VALUES (1, 'OTRO', 'Cliente histórico')"
        )
    )
    connection.execute(
        text(
            "CREATE FUNCTION prevent_crm_commercial_history_mutation() "
            "RETURNS trigger AS $$ "
            "BEGIN "
            "IF current_setting('asfaltos.test_cleanup', true) = 'on' THEN "
            "RETURN OLD; "
            "END IF; "
            "RAISE EXCEPTION 'CRM commercial history is append-only'; "
            "END; "
            "$$ LANGUAGE plpgsql"
        )
    )
    connection.execute(
        text(
            "CREATE TRIGGER trg_opportunity_loss_events_append_only "
            "BEFORE UPDATE OR DELETE ON opportunity_loss_events "
            "FOR EACH ROW EXECUTE FUNCTION prevent_crm_commercial_history_mutation()"
        )
    )


def _load_migration() -> _MigrationContract:
    specification = spec_from_file_location("migration_0012", _MIGRATION_PATH)
    if specification is None or specification.loader is None:
        raise RuntimeError("Migration 0012 could not be loaded")
    module = module_from_spec(specification)
    specification.loader.exec_module(module)
    return cast(_MigrationContract, module)


def _run_migration(
    connection: Connection,
    schema: str,
    operation: Callable[[], None],
) -> None:
    connection.execute(text(f"SET LOCAL search_path TO {schema}, public"))
    context = MigrationContext.configure(connection)
    with Operations.context(context):
        operation()


def _loss_reason_detail(connection: Connection) -> str:
    value = connection.scalar(
        text("SELECT loss_reason_detail FROM opportunity_loss_events WHERE id = 1")
    )
    if not isinstance(value, str):
        raise TypeError("Legacy loss event detail was not backfilled")
    return value


def _trigger_is_enabled(connection: Connection) -> bool:
    value = connection.scalar(
        text(
            "SELECT tgenabled = 'O' FROM pg_trigger "
            "WHERE tgname = 'trg_opportunity_loss_events_append_only' "
            "AND tgrelid = 'opportunity_loss_events'::regclass"
        )
    )
    return value is True


def _assert_loss_event_remains_append_only(connection: Connection) -> None:
    with pytest.raises(DBAPIError, match="append-only"), connection.begin_nested():
        connection.execute(
            text(
                "UPDATE opportunity_loss_events "
                "SET customer_display_name = 'No permitido' WHERE id = 1"
            )
        )


def _column_exists(connection: Connection, table_name: str) -> bool:
    value = connection.scalar(
        text(
            "SELECT EXISTS ("
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = current_schema() "
            "AND table_name = :table_name "
            "AND column_name = 'loss_reason_detail')"
        ).bindparams(table_name=table_name)
    )
    return value is True
