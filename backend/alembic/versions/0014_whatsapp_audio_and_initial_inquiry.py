"""Add WhatsApp audio and immutable initial Opportunity inquiry reference.

Revision ID: 0014_whatsapp_audio_inquiry
Revises: 0013_instagram_reporting_source
Create Date: 2026-09-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014_whatsapp_audio_inquiry"
down_revision: str | Sequence[str] | None = "0013_instagram_reporting_source"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PostgreSQL forbids using a newly added enum label until the transaction that
    # added it commits. Alembic otherwise wraps this revision in one transaction,
    # so the dependent CHECK below would fail with UnsafeNewEnumValueUsage.
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE whatsapp_message_type_enum ADD VALUE IF NOT EXISTS 'AUDIO'"
        )
    op.drop_constraint(
        "ck_whatsapp_attachments_supported_type",
        "whatsapp_attachments",
        type_="check",
    )
    op.create_check_constraint(
        "ck_whatsapp_attachments_supported_type",
        "whatsapp_attachments",
        "media_type IN ('IMAGE', 'DOCUMENT', 'AUDIO')",
    )
    op.add_column(
        "opportunities",
        sa.Column("initial_whatsapp_message_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_opportunities_initial_whatsapp_message_id_messages",
        "opportunities",
        "whatsapp_messages",
        ["initial_whatsapp_message_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_opportunities_initial_whatsapp_message",
        "opportunities",
        ["initial_whatsapp_message_id"],
    )


def downgrade() -> None:
    referenced_audio = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT EXISTS ("
                "SELECT 1 FROM whatsapp_messages WHERE message_type::text = 'AUDIO' "
                "UNION ALL SELECT 1 FROM whatsapp_attachments "
                "WHERE media_type::text = 'AUDIO' "
                "UNION ALL SELECT 1 FROM whatsapp_broadcasts "
                "WHERE template_header_type::text = 'AUDIO')"
            )
        )
        .scalar_one()
    )
    if referenced_audio:
        raise RuntimeError("Cannot remove AUDIO while WhatsApp history references it")
    op.drop_constraint(
        "uq_opportunities_initial_whatsapp_message",
        "opportunities",
        type_="unique",
    )
    op.drop_constraint(
        "fk_opportunities_initial_whatsapp_message_id_messages",
        "opportunities",
        type_="foreignkey",
    )
    op.drop_column("opportunities", "initial_whatsapp_message_id")
    op.drop_constraint(
        "ck_whatsapp_attachments_supported_type",
        "whatsapp_attachments",
        type_="check",
    )
    op.drop_constraint(
        "ck_whatsapp_messages_text_body",
        "whatsapp_messages",
        type_="check",
    )
    op.execute(
        "ALTER TABLE whatsapp_messages ALTER COLUMN message_type TYPE TEXT "
        "USING message_type::text"
    )
    op.execute(
        "ALTER TABLE whatsapp_attachments ALTER COLUMN media_type TYPE TEXT "
        "USING media_type::text"
    )
    op.execute(
        "ALTER TABLE whatsapp_broadcasts ALTER COLUMN template_header_type TYPE TEXT "
        "USING template_header_type::text"
    )
    op.execute("DROP TYPE whatsapp_message_type_enum")
    previous_enum = postgresql.ENUM(
        "TEXT", "IMAGE", "DOCUMENT", name="whatsapp_message_type_enum"
    )
    previous_enum.create(op.get_bind(), checkfirst=False)
    op.execute(
        "ALTER TABLE whatsapp_messages ALTER COLUMN message_type "
        "TYPE whatsapp_message_type_enum USING message_type::whatsapp_message_type_enum"
    )
    op.execute(
        "ALTER TABLE whatsapp_attachments ALTER COLUMN media_type "
        "TYPE whatsapp_message_type_enum USING media_type::whatsapp_message_type_enum"
    )
    op.execute(
        "ALTER TABLE whatsapp_broadcasts ALTER COLUMN template_header_type "
        "TYPE whatsapp_message_type_enum "
        "USING template_header_type::whatsapp_message_type_enum"
    )
    op.create_check_constraint(
        "ck_whatsapp_attachments_supported_type",
        "whatsapp_attachments",
        "media_type IN ('IMAGE', 'DOCUMENT')",
    )
    op.create_check_constraint(
        "ck_whatsapp_messages_text_body",
        "whatsapp_messages",
        "message_type <> 'TEXT' OR template_name IS NOT NULL "
        "OR (body IS NOT NULL AND btrim(body) <> '')",
    )
