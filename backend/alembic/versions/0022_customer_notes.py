"""Add internal notes that stay with the customer (CRM-062)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022_customer_notes"
down_revision: str | Sequence[str] | None = "0021_meta_ad_source"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customer_notes",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column(
            "customer_id",
            sa.BigInteger(),
            sa.ForeignKey("customers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "author_user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("command_id", sa.Uuid(), unique=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "btrim(body) <> '' AND char_length(body) <= 600",
            name="ck_customer_notes_body",
        ),
    )
    op.create_index(
        "ix_customer_notes_active",
        "customer_notes",
        ["customer_id", "pinned", "id"],
        postgresql_where=sa.text("archived_at IS NULL"),
    )
    op.add_column(
        "opportunity_reopen_events", sa.Column("customer_note_digest", sa.Text())
    )


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM customer_notes)")):
        raise RuntimeError("A downgrade would discard saved customer notes")
    op.drop_column("opportunity_reopen_events", "customer_note_digest")
    op.drop_table("customer_notes")
