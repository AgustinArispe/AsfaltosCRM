"""Create the immutable lead intake event log.

Revision ID: 0003_create_lead_intakes
Revises: 0002_create_crm_models
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003_create_lead_intakes"
down_revision: str | Sequence[str] | None = "0002_create_crm_models"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


lead_source_enum = postgresql.ENUM(
    "WEB",
    "WHATSAPP",
    name="lead_source_enum",
    create_type=False,
)


def upgrade() -> None:
    op.drop_index("ix_customers_phone_normalized", table_name="customers")
    op.create_index(
        "ix_customers_phone_normalized",
        "customers",
        [sa.text("regexp_replace(phone, '[[:space:]()-]', '', 'g')")],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL AND phone IS NOT NULL"),
    )

    op.create_table(
        "lead_intakes",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("source", lead_source_enum, nullable=False),
        sa.Column("external_submission_id", sa.Text(), nullable=False),
        sa.Column("submitted_name", sa.Text(), nullable=False),
        sa.Column("submitted_company", sa.Text(), nullable=True),
        sa.Column("submitted_email", sa.Text(), nullable=True),
        sa.Column("submitted_phone", sa.Text(), nullable=True),
        sa.Column("submitted_province", sa.Text(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("opportunity_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "btrim(external_submission_id) <> ''",
            name="ck_lead_intakes_external_id_not_blank",
        ),
        sa.CheckConstraint(
            "btrim(submitted_name) <> ''",
            name="ck_lead_intakes_name_not_blank",
        ),
        sa.CheckConstraint(
            "submitted_company IS NULL OR btrim(submitted_company) <> ''",
            name="ck_lead_intakes_company_not_blank",
        ),
        sa.CheckConstraint(
            "submitted_email IS NULL OR btrim(submitted_email) <> ''",
            name="ck_lead_intakes_email_not_blank",
        ),
        sa.CheckConstraint(
            "submitted_phone IS NULL OR btrim(submitted_phone) <> ''",
            name="ck_lead_intakes_phone_not_blank",
        ),
        sa.CheckConstraint(
            "submitted_province IS NULL OR btrim(submitted_province) <> ''",
            name="ck_lead_intakes_province_not_blank",
        ),
        sa.CheckConstraint(
            "message IS NULL OR btrim(message) <> ''",
            name="ck_lead_intakes_message_not_blank",
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
            name="fk_lead_intakes_opportunity_id_opportunities",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source",
            "external_submission_id",
            name="uq_lead_intakes_source_external_id",
        ),
        sa.UniqueConstraint(
            "opportunity_id",
            name="uq_lead_intakes_opportunity_id",
        ),
    )


def downgrade() -> None:
    op.drop_table("lead_intakes")

    op.drop_index("ix_customers_phone_normalized", table_name="customers")
    op.create_index(
        "ix_customers_phone_normalized",
        "customers",
        [sa.text("btrim(phone)")],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL AND phone IS NOT NULL"),
    )
