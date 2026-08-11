"""Add WhatsApp marketing consent and Broadcast execution.

Revision ID: 0006_whatsapp_broadcasts
Revises: 0005_whatsapp_core
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_whatsapp_broadcasts"
down_revision: str | Sequence[str] | None = "0005_whatsapp_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

message_type_enum = postgresql.ENUM(
    "TEXT", "IMAGE", "DOCUMENT", name="whatsapp_message_type_enum", create_type=False
)
message_origin_enum = postgresql.ENUM(
    "HUMAN", "BROADCAST", name="whatsapp_message_origin_enum", create_type=False
)
consent_decision_enum = postgresql.ENUM(
    "OPT_IN", "OPT_OUT", name="whatsapp_consent_decision_enum", create_type=False
)
consent_source_enum = postgresql.ENUM(
    "FAA_CRM", "EXTERNAL_FAA", name="whatsapp_consent_source_enum", create_type=False
)
broadcast_status_enum = postgresql.ENUM(
    "DRAFT",
    "CONFIRMED",
    "PROCESSING",
    "COMPLETED",
    name="whatsapp_broadcast_status_enum",
    create_type=False,
)
recipient_status_enum = postgresql.ENUM(
    "DRAFT",
    "READY",
    "IN_PROGRESS",
    "ACCEPTED",
    "SENT",
    "DELIVERED",
    "READ",
    "FAILED",
    "UNKNOWN",
    "BLOCKED",
    name="whatsapp_broadcast_recipient_status_enum",
    create_type=False,
)
audit_event_enum = postgresql.ENUM(
    "CREATED",
    "RECIPIENTS_REPLACED",
    "VALIDATED",
    "CONFIRMED",
    "STARTED",
    "RETRY_AUTHORIZED",
    "STALE_CLAIM_RECOVERED",
    "BLOCKED",
    "PROCESSED",
    "COMPLETED",
    name="whatsapp_broadcast_audit_event_type_enum",
    create_type=False,
)

NEW_ENUMS = (
    message_origin_enum,
    consent_decision_enum,
    consent_source_enum,
    broadcast_status_enum,
    recipient_status_enum,
    audit_event_enum,
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in NEW_ENUMS:
        enum_type.create(bind, checkfirst=False)

    op.create_table(
        "whatsapp_marketing_consent_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("client_event_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=False),
        sa.Column("normalized_phone", sa.Text(), nullable=False),
        sa.Column("decision", consent_decision_enum, nullable=False),
        sa.Column("source", consent_source_enum, nullable=False),
        sa.Column("evidence_reference", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by_user_id", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "btrim(normalized_phone) <> ''",
            name="ck_whatsapp_consent_events_phone_not_blank",
        ),
        sa.CheckConstraint(
            "evidence_reference IS NULL OR btrim(evidence_reference) <> ''",
            name="ck_whatsapp_consent_events_evidence_not_blank",
        ),
        sa.CheckConstraint(
            "source <> 'EXTERNAL_FAA' OR evidence_reference IS NOT NULL",
            name="ck_whatsapp_consent_events_external_evidence",
        ),
        sa.CheckConstraint(
            "effective_at <= recorded_at",
            name="ck_whatsapp_consent_events_not_future",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="fk_whatsapp_consent_events_customer_id_customers",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by_user_id"],
            ["users.id"],
            name="fk_whatsapp_consent_events_recorded_by_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_whatsapp_consent_events_client_id",
        "whatsapp_marketing_consent_events",
        ["client_event_id"],
        unique=True,
    )
    op.create_index(
        "ix_whatsapp_consent_events_current",
        "whatsapp_marketing_consent_events",
        ["customer_id", "normalized_phone", "effective_at", "id"],
    )

    op.create_table(
        "whatsapp_broadcasts",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("client_generated_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("external_campaign_reference", sa.Text(), nullable=True),
        sa.Column(
            "status",
            broadcast_status_enum,
            server_default=sa.text("'DRAFT'"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("template_external_id", sa.Text(), nullable=False),
        sa.Column("template_name", sa.Text(), nullable=False),
        sa.Column("template_language", sa.Text(), nullable=False),
        sa.Column("template_category", sa.Text(), nullable=False),
        sa.Column("template_provider_status", sa.Text(), nullable=False),
        sa.Column("template_header_type", message_type_enum, nullable=True),
        sa.Column("template_header_media_required", sa.Boolean(), nullable=False),
        sa.Column("template_component_signature", sa.Text(), nullable=False),
        sa.Column("header_media_ref", sa.Uuid(), nullable=True),
        sa.Column("header_media_storage_key", sa.Text(), nullable=True),
        sa.Column("header_media_mime_type", sa.Text(), nullable=True),
        sa.Column("header_media_filename", sa.Text(), nullable=True),
        sa.Column("header_media_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("header_media_sha256", sa.Text(), nullable=True),
        sa.Column("validation_token", sa.Uuid(), nullable=True),
        sa.Column("validation_digest", sa.Text(), nullable=True),
        sa.Column("validation_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.BigInteger(), nullable=False),
        sa.Column("confirmed_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("started_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("btrim(label) <> ''", name="ck_whatsapp_broadcasts_label"),
        sa.CheckConstraint(
            "version > 0", name="ck_whatsapp_broadcasts_version_positive"
        ),
        sa.CheckConstraint(
            "btrim(template_external_id) <> '' AND btrim(template_name) <> '' "
            "AND btrim(template_language) <> ''",
            name="ck_whatsapp_broadcasts_template_identity",
        ),
        sa.CheckConstraint(
            "header_media_ref IS NULL OR (header_media_storage_key IS NOT NULL "
            "AND header_media_mime_type IS NOT NULL "
            "AND header_media_size_bytes IS NOT NULL)",
            name="ck_whatsapp_broadcasts_header_media_complete",
        ),
        *[
            sa.ForeignKeyConstraint(
                [column],
                ["users.id"],
                name=name,
                ondelete="RESTRICT",
            )
            for column, name in (
                ("created_by_user_id", "fk_whatsapp_broadcasts_created_by_users"),
                ("confirmed_by_user_id", "fk_whatsapp_broadcasts_confirmed_by_users"),
                ("started_by_user_id", "fk_whatsapp_broadcasts_started_by_users"),
            )
        ],
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_whatsapp_broadcasts_client_generated_id",
        "whatsapp_broadcasts",
        ["client_generated_id"],
        unique=True,
    )
    op.create_index(
        "ix_whatsapp_broadcasts_status_id",
        "whatsapp_broadcasts",
        ["status", "id"],
    )

    op.create_table(
        "whatsapp_broadcast_template_parameters",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("broadcast_id", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "position >= 0", name="ck_whatsapp_broadcast_params_position"
        ),
        sa.CheckConstraint(
            "btrim(name) <> '' AND btrim(value) <> ''",
            name="ck_whatsapp_broadcast_params_nonblank",
        ),
        sa.ForeignKeyConstraint(
            ["broadcast_id"],
            ["whatsapp_broadcasts.id"],
            name="fk_whatsapp_broadcast_params_broadcasts",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "broadcast_id", "name", name="uq_whatsapp_broadcast_params_name"
        ),
    )

    op.create_table(
        "whatsapp_broadcast_recipients",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("broadcast_id", sa.BigInteger(), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=False),
        sa.Column("customer_display_name", sa.Text(), nullable=False),
        sa.Column("normalized_phone", sa.Text(), nullable=False),
        sa.Column("consent_event_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "status",
            recipient_status_enum,
            server_default=sa.text("'DRAFT'"),
            nullable=False,
        ),
        sa.Column("reason_code", sa.Text(), nullable=True),
        sa.Column("safe_error_code", sa.Text(), nullable=True),
        sa.Column("safe_error_message", sa.Text(), nullable=True),
        sa.Column("conversation_id", sa.BigInteger(), nullable=True),
        sa.Column("claim_token", sa.Uuid(), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "btrim(normalized_phone) <> ''",
            name="ck_whatsapp_broadcast_recipients_phone",
        ),
        sa.ForeignKeyConstraint(
            ["broadcast_id"],
            ["whatsapp_broadcasts.id"],
            name="fk_whatsapp_broadcast_recipients_broadcasts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="fk_whatsapp_broadcast_recipients_customers",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["consent_event_id"],
            ["whatsapp_marketing_consent_events.id"],
            name="fk_whatsapp_broadcast_recipients_consent_events",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["whatsapp_conversations.id"],
            name="fk_whatsapp_broadcast_recipients_conversations",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "broadcast_id",
            "normalized_phone",
            name="uq_whatsapp_broadcast_recipients_phone",
        ),
    )
    op.create_index(
        "ix_whatsapp_broadcast_recipients_claim",
        "whatsapp_broadcast_recipients",
        ["broadcast_id", "status", "id"],
    )

    op.add_column(
        "whatsapp_messages",
        sa.Column(
            "origin",
            message_origin_enum,
            server_default=sa.text("'HUMAN'"),
            nullable=False,
        ),
    )
    op.add_column(
        "whatsapp_messages",
        sa.Column("broadcast_recipient_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "whatsapp_messages", sa.Column("template_name", sa.Text(), nullable=True)
    )
    op.add_column(
        "whatsapp_messages", sa.Column("template_language", sa.Text(), nullable=True)
    )
    op.create_foreign_key(
        "fk_whatsapp_messages_broadcast_recipient_id_recipients",
        "whatsapp_messages",
        "whatsapp_broadcast_recipients",
        ["broadcast_recipient_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        "ck_whatsapp_messages_text_body", "whatsapp_messages", type_="check"
    )
    op.create_check_constraint(
        "ck_whatsapp_messages_text_body",
        "whatsapp_messages",
        "message_type <> 'TEXT' OR origin = 'BROADCAST' "
        "OR (body IS NOT NULL AND btrim(body) <> '')",
    )
    op.create_check_constraint(
        "ck_whatsapp_messages_origin_contract",
        "whatsapp_messages",
        "(origin = 'HUMAN' AND broadcast_recipient_id IS NULL "
        "AND template_name IS NULL AND template_language IS NULL) OR "
        "(origin = 'BROADCAST' AND direction = 'OUTBOUND' "
        "AND broadcast_recipient_id IS NOT NULL "
        "AND template_name IS NOT NULL AND template_language IS NOT NULL)",
    )
    op.create_index(
        "uq_whatsapp_messages_broadcast_initial",
        "whatsapp_messages",
        ["broadcast_recipient_id"],
        unique=True,
        postgresql_where=sa.text(
            "broadcast_recipient_id IS NOT NULL AND retry_of_message_id IS NULL"
        ),
    )

    op.create_table(
        "whatsapp_broadcast_audit_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("broadcast_id", sa.BigInteger(), nullable=False),
        sa.Column("recipient_id", sa.BigInteger(), nullable=True),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("command_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", audit_event_enum, nullable=False),
        sa.Column("reason_code", sa.Text(), nullable=True),
        sa.Column("actor_user_id", sa.BigInteger(), nullable=True),
        sa.Column("affected_count", sa.Integer(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["broadcast_id"],
            ["whatsapp_broadcasts.id"],
            name="fk_whatsapp_broadcast_audit_broadcasts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_id"],
            ["whatsapp_broadcast_recipients.id"],
            name="fk_whatsapp_broadcast_audit_recipients",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["whatsapp_messages.id"],
            name="fk_whatsapp_broadcast_audit_messages",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_whatsapp_broadcast_audit_actor_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_whatsapp_broadcast_audit_command",
        "whatsapp_broadcast_audit_events",
        ["broadcast_id", "command_id"],
        unique=True,
        postgresql_where=sa.text("command_id IS NOT NULL"),
    )
    op.create_index(
        "ix_whatsapp_broadcast_audit_broadcast",
        "whatsapp_broadcast_audit_events",
        ["broadcast_id", "id"],
    )

    op.execute(
        """
        CREATE FUNCTION prevent_whatsapp_append_only_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'WhatsApp audit history is append-only';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table in (
        "whatsapp_marketing_consent_events",
        "whatsapp_broadcast_audit_events",
    ):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_append_only
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION prevent_whatsapp_append_only_mutation();
            """
        )


def downgrade() -> None:
    for table in (
        "whatsapp_marketing_consent_events",
        "whatsapp_broadcast_audit_events",
    ):
        op.execute(f"DROP TRIGGER trg_{table}_append_only ON {table}")
    op.execute("DROP FUNCTION prevent_whatsapp_append_only_mutation()")
    op.drop_table("whatsapp_broadcast_audit_events")
    op.drop_index(
        "uq_whatsapp_messages_broadcast_initial", table_name="whatsapp_messages"
    )
    op.drop_constraint(
        "ck_whatsapp_messages_origin_contract", "whatsapp_messages", type_="check"
    )
    op.drop_constraint(
        "ck_whatsapp_messages_text_body", "whatsapp_messages", type_="check"
    )
    op.create_check_constraint(
        "ck_whatsapp_messages_text_body",
        "whatsapp_messages",
        "message_type <> 'TEXT' OR (body IS NOT NULL AND btrim(body) <> '')",
    )
    op.drop_constraint(
        "fk_whatsapp_messages_broadcast_recipient_id_recipients",
        "whatsapp_messages",
        type_="foreignkey",
    )
    op.drop_column("whatsapp_messages", "template_language")
    op.drop_column("whatsapp_messages", "template_name")
    op.drop_column("whatsapp_messages", "broadcast_recipient_id")
    op.drop_column("whatsapp_messages", "origin")
    op.drop_table("whatsapp_broadcast_recipients")
    op.drop_table("whatsapp_broadcast_template_parameters")
    op.drop_table("whatsapp_broadcasts")
    op.drop_table("whatsapp_marketing_consent_events")
    bind = op.get_bind()
    for enum_type in reversed(NEW_ENUMS):
        enum_type.drop(bind, checkfirst=False)
