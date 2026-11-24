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


def test_meta_source_migration_preserves_data_and_enforces_one_channel_case() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic/versions/0021_meta_ad_lead_source.py"
    )
    specification = spec_from_file_location("crm061_migration", path)
    assert specification is not None and specification.loader is not None
    module = module_from_spec(specification)
    specification.loader.exec_module(module)
    migration = cast(Migration, module)
    schema = f"crm061_migration_{uuid4().hex}"
    with engine.connect() as connection:
        try:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(text(f'SET search_path TO "{schema}"'))
            statements = (
                "CREATE TYPE lead_source_enum AS ENUM ('WEB','WHATSAPP','REFERIDO','INSTAGRAM')",
                "CREATE TABLE opportunities (id BIGINT PRIMARY KEY, customer_id BIGINT NOT NULL, source lead_source_enum NOT NULL, status TEXT NOT NULL, deleted_at TIMESTAMPTZ)",
                "CREATE TABLE lead_intakes (source lead_source_enum)",
                "CREATE TABLE opportunity_loss_events (source lead_source_enum)",
                "CREATE TABLE whatsapp_messages (id BIGINT PRIMARY KEY, body TEXT)",
                "CREATE UNIQUE INDEX uq_opportunities_one_active_whatsapp_per_customer ON opportunities(customer_id) WHERE deleted_at IS NULL AND source='WHATSAPP' AND status IN ('NUEVA','PARA_COTIZAR','COTIZADA','NEGOCIACION')",
                "INSERT INTO opportunities VALUES (1,1,'WEB','NUEVA',NULL),(2,1,'WHATSAPP','NUEVA',NULL)",
                "INSERT INTO whatsapp_messages VALUES (1,'Consulta anterior')",
            )
            for statement in statements:
                connection.execute(text(statement))
            connection.commit()
            context = MigrationContext.configure(connection)
            with context.begin_transaction(), Operations.context(context):
                migration.upgrade()
            assert list(
                connection.execute(
                    text("SELECT source::text FROM opportunities ORDER BY id")
                ).scalars()
            ) == ["WEB", "WHATSAPP"]
            assert connection.execute(
                text(
                    "SELECT body, referral_source_type, referral_source_id, referral_source_url, referral_ctwa_clid FROM whatsapp_messages"
                )
            ).one() == ("Consulta anterior", None, None, None, None)
            connection.commit()
            with pytest.raises(DBAPIError), connection.begin():
                connection.execute(
                    text("INSERT INTO opportunities VALUES (3,1,'META','NUEVA',NULL)")
                )
            connection.execute(
                text(
                    "INSERT INTO opportunities VALUES (3,2,'META','COTIZADA',NULL),(4,2,'META','GANADA',NULL)"
                )
            )
            connection.commit()
            with pytest.raises(DBAPIError), connection.begin():
                connection.execute(
                    text(
                        "INSERT INTO opportunities VALUES (5,2,'WHATSAPP','PARA_COTIZAR',NULL)"
                    )
                )
            with (
                Operations.context(context),
                pytest.raises(RuntimeError, match="stored evidence"),
            ):
                migration.downgrade()
            connection.rollback()
            connection.execute(text("DELETE FROM opportunities WHERE source='META'"))
            connection.execute(
                text("UPDATE whatsapp_messages SET referral_source_type='ad'")
            )
            connection.commit()
            with (
                Operations.context(context),
                pytest.raises(RuntimeError, match="stored evidence"),
            ):
                migration.downgrade()
        finally:
            connection.rollback()
            connection.execute(text("SET search_path TO public"))
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            connection.commit()
