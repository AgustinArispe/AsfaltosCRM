"""Enforce one active WhatsApp opportunity per customer.

Revision ID: 0015_one_active_opportunity
Revises: 0014_whatsapp_audio_inquiry
Create Date: 2026-09-22
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0015_one_active_opportunity"
down_revision: str | Sequence[str] | None = "0014_whatsapp_audio_inquiry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_opportunities_one_active_whatsapp_per_customer",
        "opportunities",
        ["customer_id"],
        unique=True,
        postgresql_where=sa.text(
            "deleted_at IS NULL AND source = 'WHATSAPP' AND status IN "
            "('NUEVA', 'COTIZADA', 'NEGOCIACION')"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_opportunities_one_active_whatsapp_per_customer",
        table_name="opportunities",
    )
