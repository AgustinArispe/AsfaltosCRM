"""Add soft deletion to WhatsApp conversations.

Revision ID: 0017_whatsapp_soft_delete
Revises: 0016_notification_soft_delete
Create Date: 2026-09-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0017_whatsapp_soft_delete"
down_revision: str | Sequence[str] | None = "0016_notification_soft_delete"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "whatsapp_conversations",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("whatsapp_conversations", "deleted_at")
