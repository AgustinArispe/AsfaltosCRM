"""Add per-user notification delivery and read state.

Revision ID: 0010_notification_recipients
Revises: 0009_human_whatsapp_templates
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_notification_recipients"
down_revision: str | Sequence[str] | None = "0009_human_whatsapp_templates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE notification_type_enum ADD VALUE IF NOT EXISTS 'NEW_LEAD'")
    op.create_table(
        "notification_recipients",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("notification_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "read_at IS NULL OR read_at >= created_at",
            name="ck_notification_recipients_read_after_created",
        ),
        sa.ForeignKeyConstraint(
            ["notification_id"],
            ["notifications.id"],
            name="fk_notification_recipients_notification_id_notifications",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_notification_recipients_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "notification_id",
            "user_id",
            name="uq_notification_recipients_notification_user",
        ),
    )
    op.create_index(
        "ix_notification_recipients_user_read",
        "notification_recipients",
        ["user_id", "read_at"],
    )
    op.execute(
        """
        INSERT INTO notification_recipients
            (notification_id, user_id, created_at, read_at)
        SELECT notifications.id, users.id, notifications.created_at,
               notifications.read_at
        FROM notifications
        CROSS JOIN users
        WHERE users.is_active IS TRUE
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE notifications
        SET read_at = states.read_at
        FROM (
            SELECT notification_id,
                   CASE
                       WHEN bool_and(read_at IS NOT NULL) THEN max(read_at)
                       ELSE NULL
                   END AS read_at
            FROM notification_recipients
            GROUP BY notification_id
        ) AS states
        WHERE notifications.id = states.notification_id
        """
    )
    op.drop_index(
        "ix_notification_recipients_user_read",
        table_name="notification_recipients",
    )
    op.drop_table("notification_recipients")
    # PostgreSQL enum values cannot be removed safely in-place. Keeping NEW_LEAD is
    # backward-compatible and avoids deleting logical notification history.
