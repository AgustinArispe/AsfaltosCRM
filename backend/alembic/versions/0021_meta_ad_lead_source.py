"""Attribute WhatsApp ad inquiries to Meta (CRM-061)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021_meta_ad_source"
down_revision: str | Sequence[str] | None = "0020_follow_up"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REFERRAL_COLUMNS = (
    "referral_source_type",
    "referral_source_id",
    "referral_source_url",
    "referral_ctwa_clid",
)


def upgrade() -> None:
    # PostgreSQL must commit an enum value before a partial index can use it.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE lead_source_enum ADD VALUE IF NOT EXISTS 'META'")
    for name in REFERRAL_COLUMNS:
        op.add_column("whatsapp_messages", sa.Column(name, sa.Text(), nullable=True))
    op.add_column(
        "whatsapp_messages",
        sa.Column(
            "referral_captured",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
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
            "deleted_at IS NULL AND source IN ('WHATSAPP', 'META') "
            "AND status IN ('NUEVA', 'PARA_COTIZAR', 'COTIZADA', 'NEGOCIACION')"
        ),
    )


def downgrade() -> None:
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS ("
            "SELECT 1 FROM opportunities WHERE source::text = 'META' UNION ALL "
            "SELECT 1 FROM lead_intakes WHERE source::text = 'META' UNION ALL "
            "SELECT 1 FROM opportunity_loss_events WHERE source::text = 'META' UNION ALL "
            "SELECT 1 FROM whatsapp_messages WHERE referral_source_type IS NOT NULL "
            "OR referral_source_id IS NOT NULL OR referral_source_url IS NOT NULL "
            "OR referral_ctwa_clid IS NOT NULL)"
        )
    ):
        raise RuntimeError(
            "Cannot remove Meta attribution while stored evidence references it"
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
    for name in reversed(REFERRAL_COLUMNS):
        op.drop_column("whatsapp_messages", name)
    op.drop_column("whatsapp_messages", "referral_captured")
    # Keep the additive enum label. Removing it would require rewriting shared
    # commercial history columns even though no data uses the new value.
