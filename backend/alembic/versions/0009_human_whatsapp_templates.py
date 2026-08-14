"""Add durable human WhatsApp template parameters.

Revision ID: 0009_human_whatsapp_templates
Revises: 0008_security_hardening
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_human_whatsapp_templates"
down_revision: str | Sequence[str] | None = "0008_security_hardening"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_whatsapp_messages_text_body",
        "whatsapp_messages",
        type_="check",
    )
    op.drop_constraint(
        "ck_whatsapp_messages_origin_contract",
        "whatsapp_messages",
        type_="check",
    )
    op.create_check_constraint(
        "ck_whatsapp_messages_text_body",
        "whatsapp_messages",
        "message_type <> 'TEXT' OR template_name IS NOT NULL "
        "OR (body IS NOT NULL AND btrim(body) <> '')",
    )
    op.create_check_constraint(
        "ck_whatsapp_messages_origin_contract",
        "whatsapp_messages",
        "(origin = 'HUMAN' AND broadcast_recipient_id IS NULL "
        "AND ((template_name IS NULL AND template_language IS NULL) OR "
        "(template_name IS NOT NULL AND template_language IS NOT NULL))) OR "
        "(origin = 'BROADCAST' AND direction = 'OUTBOUND' "
        "AND broadcast_recipient_id IS NOT NULL "
        "AND template_name IS NOT NULL AND template_language IS NOT NULL)",
    )
    op.create_table(
        "whatsapp_human_template_parameters",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "position >= 0",
            name="ck_whatsapp_human_template_params_position",
        ),
        sa.CheckConstraint(
            "btrim(name) <> '' AND btrim(value) <> ''",
            name="ck_whatsapp_human_template_params_nonblank",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["whatsapp_messages.id"],
            name="fk_whatsapp_human_template_params_message_id_messages",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "message_id",
            "name",
            name="uq_whatsapp_human_template_params_message_name",
        ),
    )


def downgrade() -> None:
    op.drop_table("whatsapp_human_template_parameters")
    op.drop_constraint(
        "ck_whatsapp_messages_text_body",
        "whatsapp_messages",
        type_="check",
    )
    op.drop_constraint(
        "ck_whatsapp_messages_origin_contract",
        "whatsapp_messages",
        type_="check",
    )
    op.create_check_constraint(
        "ck_whatsapp_messages_text_body",
        "whatsapp_messages",
        "message_type <> 'TEXT' OR origin = 'BROADCAST' "
        "OR (body IS NOT NULL AND btrim(body) <> '')",
    )
    op.create_check_constraint(
        "ck_whatsapp_messages_origin_contract",
        "whatsapp_messages",
        "(origin = 'HUMAN' AND broadcast_recipient_id IS NULL "
        "AND template_name IS NULL AND template_language IS NULL) OR "
        "(origin = 'BROADCAST' AND direction = 'OUTBOUND' "
        "AND broadcast_recipient_id IS NOT NULL "
        "AND template_name IS NOT NULL AND template_language IS NOT NULL)",
    )
