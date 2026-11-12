"""Introduce the prequote stage and immutable transition notes (CRM-057).

Revision ID: 0019_prequote_notes
Revises: 0018_whatsapp_handled
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_prequote_notes"
down_revision: str | Sequence[str] | None = "0018_whatsapp_handled"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Additive enum change must be committed before use in a partial index.
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE opportunity_status_enum ADD VALUE IF NOT EXISTS 'PARA_COTIZAR'"
        )
    op.add_column(
        "opportunity_status_history", sa.Column("note", sa.Text(), nullable=True)
    )
    op.create_check_constraint(
        "ck_status_history_note",
        "opportunity_status_history",
        "note IS NULL OR (btrim(note) <> '' AND char_length(note) <= 4000)",
    )
    # Both old stages already required a quote. Do not move them back into preparation
    # or rewrite historical events/timestamps. Legacy NEGOCIACION remains readable.
    op.execute(
        "UPDATE opportunities SET status = 'COTIZADA' WHERE status = 'NEGOCIACION'"
    )
    op.drop_index(
        "uq_opportunities_one_active_whatsapp_per_customer", table_name="opportunities"
    )
    op.create_index(
        "uq_opportunities_one_active_whatsapp_per_customer",
        "opportunities",
        ["customer_id"],
        unique=True,
        postgresql_where=sa.text(
            "deleted_at IS NULL AND source = 'WHATSAPP' "
            "AND status IN ('NUEVA', 'PARA_COTIZAR', 'COTIZADA', 'NEGOCIACION')"
        ),
    )
    op.drop_constraint("ck_reopen_target", "opportunity_reopen_events", type_="check")
    op.create_check_constraint(
        "ck_reopen_target",
        "opportunity_reopen_events",
        "target_status IN ('COTIZADA', 'NEGOCIACION')",
    )


def downgrade() -> None:
    # A generic down migration would discard audit notes and cannot restore old stage
    # semantics. Require an operator-led, backed-up recovery instead of silent data loss.
    raise RuntimeError(
        "CRM-057 downgrade requires a reviewed backup/restore plan; notes must be preserved"
    )
