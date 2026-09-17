"""Persist free-text detail for OTRO loss reasons.

Revision ID: 0012_other_loss_reason_detail
Revises: 0011_manual_opportunity_creation
Create Date: 2026-09-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_other_loss_reason_detail"
down_revision: str | Sequence[str] | None = "0011_manual_opportunity_creation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_OTHER_DETAIL = "Detalle no registrado (pérdida anterior)"


def upgrade() -> None:
    op.add_column(
        "opportunities",
        sa.Column("loss_reason_detail", sa.Text(), nullable=True),
    )
    op.add_column(
        "opportunity_loss_events",
        sa.Column("loss_reason_detail", sa.Text(), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE opportunities SET loss_reason_detail = :detail "
            "WHERE loss_reason = 'OTRO'"
        ).bindparams(detail=LEGACY_OTHER_DETAIL)
    )
    op.execute(
        sa.text(
            "UPDATE opportunity_loss_events SET loss_reason_detail = :detail "
            "WHERE reason = 'OTRO'"
        ).bindparams(detail=LEGACY_OTHER_DETAIL)
    )
    op.create_check_constraint(
        "ck_opportunities_other_loss_detail",
        "opportunities",
        "(loss_reason = 'OTRO' AND loss_reason_detail IS NOT NULL "
        "AND btrim(loss_reason_detail) <> '' "
        "AND char_length(loss_reason_detail) <= 500) OR "
        "(loss_reason IS DISTINCT FROM 'OTRO' AND loss_reason_detail IS NULL)",
    )
    op.create_check_constraint(
        "ck_loss_events_other_loss_detail",
        "opportunity_loss_events",
        "(reason = 'OTRO' AND loss_reason_detail IS NOT NULL "
        "AND btrim(loss_reason_detail) <> '' "
        "AND char_length(loss_reason_detail) <= 500) OR "
        "(reason <> 'OTRO' AND loss_reason_detail IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_loss_events_other_loss_detail",
        "opportunity_loss_events",
        type_="check",
    )
    op.drop_constraint(
        "ck_opportunities_other_loss_detail",
        "opportunities",
        type_="check",
    )
    op.drop_column("opportunity_loss_events", "loss_reason_detail")
    op.drop_column("opportunities", "loss_reason_detail")
