"""Add referral source and idempotent manual opportunity commands.

Revision ID: 0011_manual_opportunity_creation
Revises: 0010_notification_recipients
Create Date: 2026-09-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_manual_opportunity_creation"
down_revision: str | Sequence[str] | None = "0010_notification_recipients"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE lead_source_enum ADD VALUE IF NOT EXISTS 'REFERIDO'")
    op.create_table(
        "manual_opportunity_creation_commands",
        sa.Column("command_id", sa.Uuid(), nullable=False),
        sa.Column("request_fingerprint", sa.Text(), nullable=False),
        sa.Column("opportunity_id", sa.BigInteger(), nullable=False),
        sa.Column("created_by_user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_manual_opportunity_commands_created_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
            name="fk_manual_opportunity_commands_opportunity_id_opportunities",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("command_id"),
        sa.UniqueConstraint(
            "opportunity_id",
            name="uq_manual_opportunity_commands_opportunity_id",
        ),
    )


def downgrade() -> None:
    op.drop_table("manual_opportunity_creation_commands")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM opportunities WHERE source::text = 'REFERIDO'
                UNION ALL
                SELECT 1 FROM lead_intakes WHERE source::text = 'REFERIDO'
                UNION ALL
                SELECT 1 FROM opportunity_loss_events WHERE source::text = 'REFERIDO'
            ) THEN
                RAISE EXCEPTION
                    'Cannot remove REFERIDO while commercial history references it';
            END IF;
        END
        $$
        """
    )
    op.execute(
        "ALTER TABLE opportunities ALTER COLUMN source TYPE TEXT USING source::text"
    )
    op.execute(
        "ALTER TABLE lead_intakes ALTER COLUMN source TYPE TEXT USING source::text"
    )
    op.execute(
        "ALTER TABLE opportunity_loss_events "
        "ALTER COLUMN source TYPE TEXT USING source::text"
    )
    op.execute("DROP TYPE lead_source_enum")
    previous_enum = postgresql.ENUM("WEB", "WHATSAPP", name="lead_source_enum")
    previous_enum.create(op.get_bind(), checkfirst=False)
    op.execute(
        "ALTER TABLE opportunities ALTER COLUMN source TYPE lead_source_enum "
        "USING source::lead_source_enum"
    )
    op.execute(
        "ALTER TABLE lead_intakes ALTER COLUMN source TYPE lead_source_enum "
        "USING source::lead_source_enum"
    )
    op.execute(
        "ALTER TABLE opportunity_loss_events "
        "ALTER COLUMN source TYPE lead_source_enum USING source::lead_source_enum"
    )
