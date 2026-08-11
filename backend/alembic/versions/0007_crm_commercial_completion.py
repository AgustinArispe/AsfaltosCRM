"""Complete the CRM commercial backend.

Revision ID: 0007_crm_commercial_completion
Revises: 0006_whatsapp_broadcasts
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_crm_commercial_completion"
down_revision: str | Sequence[str] | None = "0006_whatsapp_broadcasts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

transition_enum = postgresql.ENUM(
    "CREATED", "STATUS_CHANGED", "LOST", "REOPENED",
    name="opportunity_transition_kind_enum", create_type=False,
)
legendary_enum = postgresql.ENUM(
    "MANUAL_OVERRIDE_CHANGED", "AUTOMATIC_CHANGED",
    name="legendary_event_type_enum", create_type=False,
)
import_status_enum = postgresql.ENUM(
    "VALID", "INVALID", "COMMITTED",
    name="customer_import_status_enum", create_type=False,
)
import_action_enum = postgresql.ENUM(
    "CREATE", "ENRICH", "UNCHANGED", "ERROR",
    name="customer_import_action_enum", create_type=False,
)
import_issue_enum = postgresql.ENUM(
    "INVALID_FILE", "INVALID_HEADER", "INVALID_ROW", "MISSING_NAME",
    "INVALID_EMAIL", "INVALID_PHONE", "AMBIGUOUS_IDENTITY",
    "DELETED_IDENTITY", "DUPLICATE_IDENTITY",
    name="customer_import_issue_code_enum", create_type=False,
)
status_enum = postgresql.ENUM(
    "NUEVA", "COTIZADA", "NEGOCIACION", "GANADA", "PERDIDA",
    name="opportunity_status_enum", create_type=False,
)
reason_enum = postgresql.ENUM(
    "PRECIO", "SIN_RESPUESTA", "COMPETENCIA", "PROYECTO_CANCELADO", "OTRO",
    name="loss_reason_enum", create_type=False,
)
source_enum = postgresql.ENUM(
    "WEB", "WHATSAPP", name="lead_source_enum", create_type=False,
)

NEW_ENUMS = (
    transition_enum,
    legendary_enum,
    import_status_enum,
    import_action_enum,
    import_issue_enum,
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in NEW_ENUMS:
        enum_type.create(bind, checkfirst=False)

    op.add_column(
        "customers",
        sa.Column("legendary_automatic", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "customers",
        sa.Column("legendary_automatic_evaluated_at", sa.DateTime(timezone=True)),
    )
    op.add_column(
        "opportunity_status_history",
        sa.Column(
            "transition_kind",
            transition_enum,
            server_default=sa.text("'STATUS_CHANGED'"),
            nullable=False,
        ),
    )
    op.execute(
        "UPDATE opportunity_status_history SET transition_kind = CASE "
        "WHEN from_status IS NULL THEN 'CREATED'::opportunity_transition_kind_enum "
        "WHEN to_status = 'PERDIDA' THEN 'LOST'::opportunity_transition_kind_enum "
        "ELSE 'STATUS_CHANGED'::opportunity_transition_kind_enum END"
    )
    op.alter_column("opportunity_status_history", "transition_kind", server_default=None)
    op.drop_index("ix_opportunities_legendary_wins", table_name="opportunities")
    op.create_index(
        "ix_opportunities_legendary_wins",
        "opportunities",
        ["customer_id", "created_at"],
        postgresql_where=sa.text("status = 'GANADA' AND deleted_at IS NULL"),
    )

    op.create_table(
        "opportunity_notes",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("opportunity_id", sa.BigInteger(), nullable=False),
        sa.Column("author_user_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_table(
        "opportunity_note_revisions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("note_id", sa.BigInteger(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_pinned", sa.Boolean(), nullable=False),
        sa.Column("actor_user_id", sa.BigInteger(), nullable=False),
        sa.Column("command_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("revision_number > 0", name="ck_note_revision_positive"),
        sa.CheckConstraint("btrim(body) <> ''", name="ck_note_revision_body_not_blank"),
        sa.UniqueConstraint("note_id", "revision_number", name="uq_note_revision"),
        sa.ForeignKeyConstraint(["note_id"], ["opportunity_notes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index(
        "ix_note_revisions_search",
        "opportunity_note_revisions",
        [sa.text("to_tsvector('simple', body)")],
        postgresql_using="gin",
    )

    op.create_table(
        "customer_legendary_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("customer_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", legendary_enum, nullable=False),
        sa.Column("before_manual", sa.Boolean(), nullable=False),
        sa.Column("after_manual", sa.Boolean(), nullable=False),
        sa.Column("before_automatic", sa.Boolean(), nullable=False),
        sa.Column("after_automatic", sa.Boolean(), nullable=False),
        sa.Column("before_effective", sa.Boolean(), nullable=False),
        sa.Column("after_effective", sa.Boolean(), nullable=False),
        sa.Column("first_won_opportunity_id", sa.BigInteger()),
        sa.Column("first_won_created_at", sa.DateTime(timezone=True)),
        sa.Column("actor_user_id", sa.BigInteger()),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["first_won_opportunity_id"], ["opportunities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
    )

    op.create_table(
        "opportunity_loss_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("opportunity_id", sa.BigInteger(), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=False),
        sa.Column("status_history_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("from_status", status_enum, nullable=False),
        sa.Column("reason", reason_enum, nullable=False),
        sa.Column("source", source_enum, nullable=False),
        sa.Column("customer_display_name", sa.Text(), nullable=False),
        sa.Column("customer_province", sa.Text()),
        sa.Column("quoted_total_kg", sa.Numeric(14, 3), nullable=False),
        sa.Column("actor_user_id", sa.BigInteger()),
        sa.Column("lost_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["status_history_id"], ["opportunity_status_history.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_loss_events_workspace", "opportunity_loss_events", ["lost_at", "id"])
    op.create_table(
        "opportunity_loss_product_snapshots",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("loss_event_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("product_name", sa.Text(), nullable=False),
        sa.Column("quantity_kg", sa.Numeric(14, 3), nullable=False),
        sa.CheckConstraint("quantity_kg > 0", name="ck_loss_product_quantity_positive"),
        sa.UniqueConstraint("loss_event_id", "product_id", name="uq_loss_product"),
        sa.ForeignKeyConstraint(["loss_event_id"], ["opportunity_loss_events.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
    )
    op.create_table(
        "opportunity_reopen_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("opportunity_id", sa.BigInteger(), nullable=False),
        sa.Column("loss_event_id", sa.BigInteger(), nullable=False),
        sa.Column("status_history_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("target_status", status_enum, nullable=False),
        sa.Column("actor_user_id", sa.BigInteger(), nullable=False),
        sa.Column("command_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("reopened_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("target_status = 'NEGOCIACION'", name="ck_reopen_target"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["loss_event_id"], ["opportunity_loss_events.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["status_history_id"], ["opportunity_status_history.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
    )

    _backfill_current_losses()
    _create_import_tables()
    _create_append_only_triggers()


def _backfill_current_losses() -> None:
    op.execute(
        """
        INSERT INTO opportunity_loss_events (
            opportunity_id, customer_id, status_history_id, from_status, reason,
            source, customer_display_name, customer_province, quoted_total_kg,
            actor_user_id, lost_at
        )
        SELECT o.id, o.customer_id, h.id, h.from_status, o.loss_reason, o.source,
               concat_ws(' ', c.name, NULLIF(btrim(c.company), '')), c.province,
               COALESCE(SUM(opr.quantity_kg), 0), h.changed_by_user_id, h.changed_at
        FROM opportunities o
        JOIN customers c ON c.id = o.customer_id
        JOIN LATERAL (
            SELECT sh.* FROM opportunity_status_history sh
            WHERE sh.opportunity_id = o.id AND sh.to_status = 'PERDIDA'
            ORDER BY sh.changed_at DESC, sh.id DESC LIMIT 1
        ) h ON true
        LEFT JOIN opportunity_products opr ON opr.opportunity_id = o.id
        WHERE o.status = 'PERDIDA'
        GROUP BY o.id, c.id, h.id, h.from_status, h.changed_by_user_id, h.changed_at
        """
    )
    op.execute(
        """
        INSERT INTO opportunity_loss_product_snapshots
            (loss_event_id, product_id, product_name, quantity_kg)
        SELECT le.id, opr.product_id, p.name, opr.quantity_kg
        FROM opportunity_loss_events le
        JOIN opportunity_products opr ON opr.opportunity_id = le.opportunity_id
        JOIN products p ON p.id = opr.product_id
        """
    )


def _create_import_tables() -> None:
    op.create_table(
        "customer_import_batches",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("client_import_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("file_sha256", sa.Text(), nullable=False),
        sa.Column("source_filename", sa.Text(), nullable=False),
        sa.Column("status", import_status_enum, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.BigInteger(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("create_count", sa.Integer(), nullable=False),
        sa.Column("enrich_count", sa.Integer(), nullable=False),
        sa.Column("unchanged_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("commit_command_id", sa.Uuid(), unique=True),
        sa.Column("committed_by_user_id", sa.BigInteger()),
        sa.Column("committed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["committed_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_table(
        "customer_import_rows",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("batch_id", sa.BigInteger(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("company", sa.Text()),
        sa.Column("email", sa.Text()),
        sa.Column("phone", sa.Text()),
        sa.Column("phone_match_key", sa.Text()),
        sa.Column("province", sa.Text()),
        sa.Column("action", import_action_enum, nullable=False),
        sa.Column("resolved_customer_id", sa.BigInteger()),
        sa.UniqueConstraint("batch_id", "row_number", name="uq_import_row_number"),
        sa.ForeignKeyConstraint(["batch_id"], ["customer_import_batches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["resolved_customer_id"], ["customers.id"], ondelete="RESTRICT"),
    )
    op.create_table(
        "customer_import_issues",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("row_id", sa.BigInteger(), nullable=False),
        sa.Column("field_name", sa.Text()),
        sa.Column("code", import_issue_enum, nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["row_id"], ["customer_import_rows.id"], ondelete="RESTRICT"),
    )
    op.create_table(
        "customer_import_results",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("batch_id", sa.BigInteger(), nullable=False),
        sa.Column("row_id", sa.BigInteger(), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=False),
        sa.Column("action", import_action_enum, nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("row_id", name="uq_import_result_row"),
        sa.ForeignKeyConstraint(["batch_id"], ["customer_import_batches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["row_id"], ["customer_import_rows.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
    )


def _create_append_only_triggers() -> None:
    op.execute(
        """
        CREATE FUNCTION prevent_crm_commercial_history_mutation()
        RETURNS trigger AS $$
        BEGIN
            IF current_setting('asfaltos.test_cleanup', true) = 'on' THEN
                RETURN OLD;
            END IF;
            RAISE EXCEPTION 'CRM commercial history is append-only';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table in (
        "opportunity_notes",
        "opportunity_note_revisions",
        "customer_legendary_events",
        "opportunity_status_history",
        "opportunity_loss_events",
        "opportunity_loss_product_snapshots",
        "opportunity_reopen_events",
        "customer_import_rows",
        "customer_import_issues",
        "customer_import_results",
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table}_append_only BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION prevent_crm_commercial_history_mutation()"
        )


def downgrade() -> None:
    append_only_tables = (
        "opportunity_notes", "opportunity_note_revisions", "customer_legendary_events",
        "opportunity_status_history", "opportunity_loss_events",
        "opportunity_loss_product_snapshots", "opportunity_reopen_events",
        "customer_import_rows", "customer_import_issues", "customer_import_results",
    )
    for table in append_only_tables:
        op.execute(f"DROP TRIGGER trg_{table}_append_only ON {table}")
    op.execute("DROP FUNCTION prevent_crm_commercial_history_mutation()")
    for table in (
        "customer_import_results", "customer_import_issues", "customer_import_rows",
        "customer_import_batches", "opportunity_reopen_events",
        "opportunity_loss_product_snapshots", "opportunity_loss_events",
        "customer_legendary_events", "opportunity_note_revisions", "opportunity_notes",
    ):
        op.drop_table(table)
    op.drop_index("ix_opportunities_legendary_wins", table_name="opportunities")
    op.create_index(
        "ix_opportunities_legendary_wins", "opportunities",
        ["customer_id", "current_status_entered_at"],
        postgresql_where=sa.text("status = 'GANADA' AND deleted_at IS NULL"),
    )
    op.drop_column("opportunity_status_history", "transition_kind")
    op.drop_column("customers", "legendary_automatic_evaluated_at")
    op.drop_column("customers", "legendary_automatic")
    bind = op.get_bind()
    for enum_type in reversed(NEW_ENUMS):
        enum_type.drop(bind, checkfirst=False)
