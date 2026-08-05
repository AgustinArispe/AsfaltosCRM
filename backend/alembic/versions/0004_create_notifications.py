"""Create persisted global opportunity notifications.

Revision ID: 0004_create_notifications
Revises: 0003_create_lead_intakes
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004_create_notifications"
down_revision: str | Sequence[str] | None = "0003_create_lead_intakes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


notification_type_enum = postgresql.ENUM(
    "OPPORTUNITY_STALE",
    name="notification_type_enum",
    create_type=False,
)


def upgrade() -> None:
    notification_type_enum.create(op.get_bind(), checkfirst=False)
    op.create_table(
        "notifications",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("type", notification_type_enum, nullable=False),
        sa.Column("opportunity_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "read_at IS NULL OR read_at >= created_at",
            name="ck_notifications_read_after_created",
        ),
        sa.CheckConstraint(
            "resolved_at IS NULL OR resolved_at >= created_at",
            name="ck_notifications_resolved_after_created",
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
            name="fk_notifications_opportunity_id_opportunities",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_notifications_active_type_opportunity",
        "notifications",
        ["opportunity_id", "type"],
        unique=True,
        postgresql_where=sa.text("resolved_at IS NULL"),
    )
    op.create_index(
        "ix_notifications_active_created_at",
        "notifications",
        [sa.text("created_at DESC"), sa.text("id DESC")],
        unique=False,
        postgresql_where=sa.text("resolved_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notifications_active_created_at",
        table_name="notifications",
    )
    op.drop_index(
        "uq_notifications_active_type_opportunity",
        table_name="notifications",
    )
    op.drop_table("notifications")
    notification_type_enum.drop(op.get_bind(), checkfirst=False)
