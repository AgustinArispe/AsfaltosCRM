"""Track manual handling of the current WhatsApp inbound request.

Revision ID: 0018_whatsapp_handled
Revises: 0017_whatsapp_soft_delete
Create Date: 2026-10-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_whatsapp_handled"
down_revision: str | Sequence[str] | None = "0017_whatsapp_soft_delete"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "whatsapp_conversations",
        sa.Column("handled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "whatsapp_conversations",
        sa.Column("handled_by_user_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "whatsapp_conversations",
        sa.Column("handled_through_message_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_whatsapp_conversations_handled_by_users",
        "whatsapp_conversations",
        "users",
        ["handled_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_whatsapp_conversations_handled_fields",
        "whatsapp_conversations",
        "(handled_at IS NULL AND handled_by_user_id IS NULL AND handled_through_message_id IS NULL) "
        "OR (handled_at IS NOT NULL AND handled_by_user_id IS NOT NULL "
        "AND handled_through_message_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_whatsapp_conversations_handled_fields",
        "whatsapp_conversations",
        type_="check",
    )
    op.drop_constraint(
        "fk_whatsapp_conversations_handled_by_users",
        "whatsapp_conversations",
        type_="foreignkey",
    )
    op.drop_column("whatsapp_conversations", "handled_through_message_id")
    op.drop_column("whatsapp_conversations", "handled_by_user_id")
    op.drop_column("whatsapp_conversations", "handled_at")
