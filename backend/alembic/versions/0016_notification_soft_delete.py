"""Add global soft deletion to notifications.

Revision ID: 0016_notification_soft_delete
Revises: 0015_one_active_opportunity
Create Date: 2026-09-24
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0016_notification_soft_delete"
down_revision: str | Sequence[str] | None = "0015_one_active_opportunity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("notifications", "deleted_at")
