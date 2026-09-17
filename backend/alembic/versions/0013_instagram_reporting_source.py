"""Add Instagram as a commercial reporting source.

Revision ID: 0013_instagram_reporting_source
Revises: 0012_other_loss_reason_detail
Create Date: 2026-09-17
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_instagram_reporting_source"
down_revision: str | Sequence[str] | None = "0012_other_loss_reason_detail"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE lead_source_enum ADD VALUE IF NOT EXISTS 'INSTAGRAM'")


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM opportunities WHERE source::text = 'INSTAGRAM'
                UNION ALL
                SELECT 1 FROM lead_intakes WHERE source::text = 'INSTAGRAM'
                UNION ALL
                SELECT 1 FROM opportunity_loss_events
                WHERE source::text = 'INSTAGRAM'
            ) THEN
                RAISE EXCEPTION
                    'Cannot remove INSTAGRAM while commercial history references it';
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
    previous_enum = postgresql.ENUM(
        "WEB",
        "WHATSAPP",
        "REFERIDO",
        name="lead_source_enum",
    )
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
