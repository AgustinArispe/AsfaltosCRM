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

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "0014_whatsapp_audio_and_initial_inquiry.py"
)


class _MigrationContract(Protocol):
    def upgrade(self) -> None: ...

    def downgrade(self) -> None: ...


def test_0014_commits_audio_enum_before_using_it_in_attachment_constraint() -> None:
    migration = _load_migration()
    schema = f"migration_0014_{uuid4().hex}"

    with engine.connect() as connection:
        try:
            _create_0013_schema(connection, schema)
            _assert_original_failure_and_transactional_rollback(connection, schema)

            _run_migration(connection, schema, migration.upgrade)
            _assert_audio_schema(connection, schema)
            _assert_existing_media_survived(connection, schema)

            _remove_audio_evidence(connection, schema)
            _run_migration(connection, schema, migration.downgrade)
            _assert_pre_audio_schema(connection, schema)

            _run_migration(connection, schema, migration.upgrade)
            _assert_audio_schema(connection, schema)
        finally:
            if connection.in_transaction():
                connection.rollback()
            connection.execute(text("SET search_path TO public"))
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            connection.commit()


def _load_migration() -> _MigrationContract:
    specification = spec_from_file_location("migration_0014", _MIGRATION_PATH)
    if specification is None or specification.loader is None:
        raise RuntimeError("Migration 0014 could not be loaded")
    module = module_from_spec(specification)
    specification.loader.exec_module(module)
    return cast(_MigrationContract, module)


def _create_0013_schema(connection: Connection, schema: str) -> None:
    connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    connection.execute(text(f'SET search_path TO "{schema}"'))
    connection.execute(
        text(
            "CREATE TYPE whatsapp_message_type_enum AS ENUM "
            "('TEXT', 'IMAGE', 'DOCUMENT')"
        )
    )
    connection.execute(
        text(
            "CREATE TABLE whatsapp_messages ("
            "id BIGINT PRIMARY KEY, "
            "message_type whatsapp_message_type_enum NOT NULL, "
            "body TEXT NULL, "
            "template_name TEXT NULL, "
            "CONSTRAINT ck_whatsapp_messages_text_body "
            "CHECK (message_type <> 'TEXT' OR template_name IS NOT NULL OR "
            "(body IS NOT NULL AND btrim(body) <> '')))"
        )
    )
    connection.execute(
        text(
            "CREATE TABLE whatsapp_attachments ("
            "id BIGINT PRIMARY KEY, "
            "message_id BIGINT NOT NULL REFERENCES whatsapp_messages(id), "
            "media_type whatsapp_message_type_enum NOT NULL, "
            "CONSTRAINT ck_whatsapp_attachments_supported_type "
            "CHECK (media_type IN ('IMAGE', 'DOCUMENT')))"
        )
    )
    connection.execute(
        text(
            "CREATE TABLE opportunities ("
            "id BIGINT PRIMARY KEY, customer_id BIGINT NOT NULL)"
        )
    )
    connection.execute(
        text(
            "CREATE TABLE whatsapp_broadcasts ("
            "id BIGINT PRIMARY KEY, "
            "template_header_type whatsapp_message_type_enum NULL)"
        )
    )
    connection.execute(
        text(
            "INSERT INTO whatsapp_messages (id, message_type) "
            "VALUES (1, 'IMAGE'), (2, 'DOCUMENT')"
        )
    )
    connection.execute(
        text(
            "INSERT INTO whatsapp_attachments (id, message_id, media_type) "
            "VALUES (1, 1, 'IMAGE'), (2, 2, 'DOCUMENT')"
        )
    )
    connection.commit()


def _assert_original_failure_and_transactional_rollback(
    connection: Connection,
    schema: str,
) -> None:
    with (
        pytest.raises(DBAPIError, match=r"unsafe use of new value.*AUDIO"),
        connection.begin(),
    ):
        connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        connection.execute(
            text(
                "ALTER TYPE whatsapp_message_type_enum ADD VALUE IF NOT EXISTS 'AUDIO'"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE whatsapp_attachments DROP CONSTRAINT "
                "ck_whatsapp_attachments_supported_type"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE whatsapp_attachments ADD CONSTRAINT "
                "ck_whatsapp_attachments_supported_type "
                "CHECK (media_type IN ('IMAGE', 'DOCUMENT', 'AUDIO'))"
            )
        )

    assert _enum_labels(connection, schema) == ["TEXT", "IMAGE", "DOCUMENT"]
    assert "AUDIO" not in _attachment_constraint(connection, schema)
    connection.rollback()


def _run_migration(
    connection: Connection,
    schema: str,
    operation: Callable[[], None],
) -> None:
    connection.execute(text(f'SET search_path TO "{schema}"'))
    connection.commit()
    context = MigrationContext.configure(connection)
    with context.begin_transaction(), Operations.context(context):
        operation()


def _assert_audio_schema(connection: Connection, schema: str) -> None:
    assert _enum_labels(connection, schema) == ["TEXT", "IMAGE", "DOCUMENT", "AUDIO"]
    assert "'AUDIO'::whatsapp_message_type_enum" in _attachment_constraint(
        connection, schema
    )
    assert (
        connection.scalar(
            text(
                "SELECT EXISTS ("
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = :schema "
                "AND table_name = 'opportunities' "
                "AND column_name = 'initial_whatsapp_message_id')"
            ).bindparams(schema=schema)
        )
        is True
    )

    connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
    connection.execute(
        text("INSERT INTO whatsapp_messages (id, message_type) VALUES (3, 'AUDIO')")
    )
    connection.execute(
        text(
            "INSERT INTO whatsapp_attachments (id, message_id, media_type) "
            "VALUES (3, 3, 'AUDIO')"
        )
    )
    connection.commit()

    with (
        pytest.raises(
            DBAPIError,
            match="ck_whatsapp_attachments_supported_type",
        ),
        connection.begin(),
    ):
        connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        connection.execute(
            text(
                "INSERT INTO whatsapp_messages (id, message_type, body) "
                "VALUES (4, 'TEXT', 'consulta')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO whatsapp_attachments (id, message_id, media_type) "
                "VALUES (4, 4, 'TEXT')"
            )
        )


def _assert_existing_media_survived(connection: Connection, schema: str) -> None:
    connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
    assert list(
        connection.scalars(
            text("SELECT media_type::text FROM whatsapp_attachments ORDER BY id")
        )
    ) == ["IMAGE", "DOCUMENT", "AUDIO"]
    connection.rollback()


def _remove_audio_evidence(connection: Connection, schema: str) -> None:
    connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
    connection.execute(text("DELETE FROM whatsapp_attachments WHERE id = 3"))
    connection.execute(text("DELETE FROM whatsapp_messages WHERE id = 3"))
    connection.commit()


def _assert_pre_audio_schema(connection: Connection, schema: str) -> None:
    assert _enum_labels(connection, schema) == ["TEXT", "IMAGE", "DOCUMENT"]
    assert "AUDIO" not in _attachment_constraint(connection, schema)


def _enum_labels(connection: Connection, schema: str) -> list[str]:
    return list(
        connection.scalars(
            text(
                "SELECT enumlabel FROM pg_enum "
                "JOIN pg_type ON pg_type.oid = pg_enum.enumtypid "
                "JOIN pg_namespace ON pg_namespace.oid = pg_type.typnamespace "
                "WHERE pg_namespace.nspname = :schema "
                "AND pg_type.typname = 'whatsapp_message_type_enum' "
                "ORDER BY enumsortorder"
            ).bindparams(schema=schema)
        )
    )


def _attachment_constraint(connection: Connection, schema: str) -> str:
    value = connection.scalar(
        text(
            "SELECT pg_get_constraintdef(pg_constraint.oid) "
            "FROM pg_constraint "
            "JOIN pg_namespace "
            "ON pg_namespace.oid = pg_constraint.connamespace "
            "WHERE pg_namespace.nspname = :schema "
            "AND conname = 'ck_whatsapp_attachments_supported_type'"
        ).bindparams(schema=schema)
    )
    if not isinstance(value, str):
        raise TypeError("WhatsApp attachment media constraint is missing")
    return value
