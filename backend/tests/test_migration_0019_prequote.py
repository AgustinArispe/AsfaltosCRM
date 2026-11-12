from decimal import Decimal
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


def test_prequote_migration_preserves_quotes_and_legacy_history_and_protects_uniqueness() -> (
    None
):
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic/versions/0019_prequote_transition_notes.py"
    )
    specification = spec_from_file_location("crm057_migration", path)
    assert specification is not None and specification.loader is not None
    module = module_from_spec(specification)
    specification.loader.exec_module(module)
    migration = cast(Migration, module)
    schema = f"crm057_migration_{uuid4().hex}"
    with engine.connect() as connection:
        try:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(text(f'SET search_path TO "{schema}"'))
            statements = [
                "CREATE TYPE opportunity_status_enum AS ENUM ('NUEVA','COTIZADA','NEGOCIACION','GANADA','PERDIDA')",
                "CREATE TABLE opportunities (id BIGINT PRIMARY KEY, customer_id BIGINT NOT NULL, source TEXT NOT NULL, status opportunity_status_enum NOT NULL, deleted_at TIMESTAMPTZ NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT '2026-01-01T00:00:00Z')",
                "CREATE UNIQUE INDEX uq_opportunities_one_active_whatsapp_per_customer ON opportunities(customer_id) WHERE deleted_at IS NULL AND source='WHATSAPP' AND status IN ('NUEVA','COTIZADA','NEGOCIACION')",
                "CREATE TABLE opportunity_status_history (id BIGINT PRIMARY KEY, opportunity_id BIGINT NOT NULL, from_status opportunity_status_enum, to_status opportunity_status_enum NOT NULL)",
                "CREATE TABLE opportunity_products (opportunity_id BIGINT, quantity_kg NUMERIC(14,3))",
                "CREATE TABLE opportunity_reopen_events (target_status opportunity_status_enum, CONSTRAINT ck_reopen_target CHECK (target_status='NEGOCIACION'))",
                "INSERT INTO opportunities(id,customer_id,source,status) VALUES (1,1,'WEB','COTIZADA'),(2,2,'WHATSAPP','NEGOCIACION')",
                "INSERT INTO opportunity_status_history VALUES (1,1,'NUEVA','COTIZADA'),(2,2,'COTIZADA','NEGOCIACION')",
                "INSERT INTO opportunity_products VALUES (1,100.5),(2,200.25)",
            ]
            for statement in statements:
                connection.execute(text(statement))
            connection.commit()
            context = MigrationContext.configure(connection)
            with context.begin_transaction(), Operations.context(context):
                migration.upgrade()
            assert list(
                connection.execute(
                    text("SELECT id, status::text FROM opportunities ORDER BY id")
                ).tuples()
            ) == [(1, "COTIZADA"), (2, "COTIZADA")]
            assert connection.scalar(
                text("SELECT SUM(quantity_kg) FROM opportunity_products")
            ) == Decimal("300.750")
            assert (
                connection.scalar(
                    text(
                        "SELECT to_status::text FROM opportunity_status_history WHERE id=2"
                    )
                )
                == "NEGOCIACION"
            )
            assert (
                connection.scalar(
                    text(
                        "SELECT COUNT(*) FROM opportunity_status_history WHERE note IS NOT NULL"
                    )
                )
                == 0
            )
            assert (
                connection.scalar(
                    text(
                        "SELECT COUNT(*) FROM opportunities WHERE updated_at='2026-01-01T00:00:00Z'"
                    )
                )
                == 2
            )
            connection.commit()
            with pytest.raises(DBAPIError), connection.begin():
                connection.execute(
                    text(
                        "INSERT INTO opportunities(id,customer_id,source,status) VALUES (3,2,'WHATSAPP','PARA_COTIZAR')"
                    )
                )
            with pytest.raises(DBAPIError), connection.begin():
                connection.execute(
                    text("UPDATE opportunity_status_history SET note='   ' WHERE id=1")
                )
            connection.execute(
                text(
                    "UPDATE opportunity_status_history SET note='Nota conservada' WHERE id=1"
                )
            )
            connection.commit()
            with pytest.raises(RuntimeError, match="backup/restore"):
                migration.downgrade()
            assert (
                connection.scalar(
                    text("SELECT note FROM opportunity_status_history WHERE id=1")
                )
                == "Nota conservada"
            )
        finally:
            connection.rollback()
            connection.execute(text("SET search_path TO public"))
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            connection.commit()
