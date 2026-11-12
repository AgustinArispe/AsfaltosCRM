"""Record opportunity follow-up without rewriting stage history (CRM-060)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_follow_up"
down_revision: str | Sequence[str] | None = "0019_prequote_notes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "opportunities",
        sa.Column("last_followed_up_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("last_followed_up_by_user_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_opportunities_follow_up_user",
        "opportunities",
        "users",
        ["last_followed_up_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_opportunities_follow_up_record",
        "opportunities",
        "(last_followed_up_at IS NULL AND last_followed_up_by_user_id IS NULL) OR "
        "(last_followed_up_at IS NOT NULL AND last_followed_up_at >= created_at "
        "AND last_followed_up_by_user_id IS NOT NULL)",
    )


def downgrade() -> None:
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM opportunities WHERE last_followed_up_at IS NOT NULL)"
        )
    ):
        raise RuntimeError(
            "CRM-060 rollback requires preserving recorded follow-ups in a reviewed backup"
        )
    op.drop_constraint(
        "ck_opportunities_follow_up_record", "opportunities", type_="check"
    )
    op.drop_constraint(
        "fk_opportunities_follow_up_user", "opportunities", type_="foreignkey"
    )
    op.drop_column("opportunities", "last_followed_up_by_user_id")
    op.drop_column("opportunities", "last_followed_up_at")
