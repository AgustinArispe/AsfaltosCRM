"""Create the provider-independent WhatsApp core.

Revision ID: 0005_whatsapp_core
Revises: 0004_create_notifications
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005_whatsapp_core"
down_revision: str | Sequence[str] | None = "0004_create_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


conversation_resolution_enum = postgresql.ENUM(
    "RESOLVED",
    "NEEDS_REVIEW",
    name="whatsapp_conversation_resolution_enum",
    create_type=False,
)
direction_enum = postgresql.ENUM(
    "INBOUND",
    "OUTBOUND",
    name="whatsapp_direction_enum",
    create_type=False,
)
message_type_enum = postgresql.ENUM(
    "TEXT",
    "IMAGE",
    "DOCUMENT",
    name="whatsapp_message_type_enum",
    create_type=False,
)
provider_state_enum = postgresql.ENUM(
    "RECEIVED",
    "SENT",
    "DELIVERED",
    "READ",
    "FAILED",
    name="whatsapp_provider_state_enum",
    create_type=False,
)
dispatch_state_enum = postgresql.ENUM(
    "PENDING",
    "IN_PROGRESS",
    "ACCEPTED",
    "DEFINITIVE_FAILED",
    "UNKNOWN",
    name="whatsapp_dispatch_state_enum",
    create_type=False,
)
opportunity_link_source_enum = postgresql.ENUM(
    "AUTO_NEW_CONTACT",
    "MANUAL",
    name="whatsapp_opportunity_link_source_enum",
    create_type=False,
)
storage_status_enum = postgresql.ENUM(
    "PENDING",
    "AVAILABLE",
    "FAILED",
    name="whatsapp_storage_status_enum",
    create_type=False,
)

WHATSAPP_ENUMS = (
    conversation_resolution_enum,
    direction_enum,
    message_type_enum,
    provider_state_enum,
    dispatch_state_enum,
    opportunity_link_source_enum,
    storage_status_enum,
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in WHATSAPP_ENUMS:
        enum_type.create(bind, checkfirst=False)

    op.create_table(
        "whatsapp_conversations",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("customer_id", sa.BigInteger(), nullable=True),
        sa.Column("external_phone", sa.Text(), nullable=False),
        sa.Column("phone_match_key", sa.Text(), nullable=False),
        sa.Column("provider_contact_id", sa.Text(), nullable=True),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column(
            "resolution_status",
            conversation_resolution_enum,
            nullable=False,
        ),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_inbound_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_outbound_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "unread_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "waiting_for_response",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("waiting_since_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "btrim(external_phone) <> ''",
            name="ck_whatsapp_conversations_phone_not_blank",
        ),
        sa.CheckConstraint(
            "btrim(phone_match_key) <> ''",
            name="ck_whatsapp_conversations_phone_key_not_blank",
        ),
        sa.CheckConstraint(
            "display_name IS NULL OR btrim(display_name) <> ''",
            name="ck_whatsapp_conversations_display_name_not_blank",
        ),
        sa.CheckConstraint(
            "customer_id IS NOT NULL OR resolution_status = 'NEEDS_REVIEW'",
            name="ck_whatsapp_conversations_unresolved_customer",
        ),
        sa.CheckConstraint(
            "unread_count >= 0",
            name="ck_whatsapp_conversations_unread_nonnegative",
        ),
        sa.CheckConstraint(
            "(waiting_for_response AND waiting_since_at IS NOT NULL) OR "
            "(NOT waiting_for_response AND waiting_since_at IS NULL)",
            name="ck_whatsapp_conversations_waiting_matches_since",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_whatsapp_conversations_updated_after_created",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="fk_whatsapp_conversations_customer_id_customers",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "phone_match_key",
            name="uq_whatsapp_conversations_phone_match_key",
        ),
    )
    op.create_index(
        "ix_whatsapp_conversations_inbox",
        "whatsapp_conversations",
        [
            sa.text("waiting_for_response DESC"),
            sa.text("unread_count DESC"),
            sa.text("last_message_at DESC"),
            sa.text("id DESC"),
        ],
        unique=False,
    )
    op.create_index(
        "ix_whatsapp_conversations_customer",
        "whatsapp_conversations",
        ["customer_id"],
        unique=False,
    )
    op.create_index(
        "ix_whatsapp_conversations_updated",
        "whatsapp_conversations",
        ["updated_at", "id"],
        unique=False,
    )

    op.create_table(
        "whatsapp_messages",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column("external_message_id", sa.Text(), nullable=True),
        sa.Column("client_generated_id", sa.Uuid(), nullable=True),
        sa.Column("direction", direction_enum, nullable=False),
        sa.Column("message_type", message_type_enum, nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("sent_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("retry_of_message_id", sa.BigInteger(), nullable=True),
        sa.Column("dispatch_state", dispatch_state_enum, nullable=True),
        sa.Column("provider_state", provider_state_enum, nullable=True),
        sa.Column("provider_error_code", sa.Text(), nullable=True),
        sa.Column("provider_error_message", sa.Text(), nullable=True),
        sa.Column("provider_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_status_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "external_message_id IS NULL OR btrim(external_message_id) <> ''",
            name="ck_whatsapp_messages_external_id_not_blank",
        ),
        sa.CheckConstraint(
            "(direction = 'INBOUND' AND external_message_id IS NOT NULL "
            "AND client_generated_id IS NULL AND dispatch_state IS NULL "
            "AND provider_state = 'RECEIVED' AND sent_by_user_id IS NULL) OR "
            "(direction = 'OUTBOUND' AND client_generated_id IS NOT NULL "
            "AND dispatch_state IS NOT NULL "
            "AND (provider_state IS NULL OR provider_state <> 'RECEIVED') "
            "AND sent_by_user_id IS NOT NULL)",
            name="ck_whatsapp_messages_direction_contract",
        ),
        sa.CheckConstraint(
            "message_type <> 'TEXT' OR (body IS NOT NULL AND btrim(body) <> '')",
            name="ck_whatsapp_messages_text_body",
        ),
        sa.CheckConstraint(
            "provider_error_code IS NULL OR btrim(provider_error_code) <> ''",
            name="ck_whatsapp_messages_error_code_not_blank",
        ),
        sa.CheckConstraint(
            "provider_error_message IS NULL OR btrim(provider_error_message) <> ''",
            name="ck_whatsapp_messages_error_message_not_blank",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_whatsapp_messages_updated_after_created",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["whatsapp_conversations.id"],
            name="fk_whatsapp_messages_conversation_id_conversations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["retry_of_message_id"],
            ["whatsapp_messages.id"],
            name="fk_whatsapp_messages_retry_of_message_id_messages",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["sent_by_user_id"],
            ["users.id"],
            name="fk_whatsapp_messages_sent_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_whatsapp_messages_external_id",
        "whatsapp_messages",
        ["external_message_id"],
        unique=True,
        postgresql_where=sa.text("external_message_id IS NOT NULL"),
    )
    op.create_index(
        "uq_whatsapp_messages_client_generated_id",
        "whatsapp_messages",
        ["client_generated_id"],
        unique=True,
        postgresql_where=sa.text("client_generated_id IS NOT NULL"),
    )
    op.create_index(
        "ix_whatsapp_messages_conversation_created",
        "whatsapp_messages",
        ["conversation_id", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_whatsapp_messages_conversation_updated",
        "whatsapp_messages",
        ["conversation_id", "updated_at", "id"],
        unique=False,
    )

    op.create_table(
        "whatsapp_conversation_opportunities",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column("opportunity_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "linked_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("unlinked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("linked_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("link_source", opportunity_link_source_enum, nullable=False),
        sa.CheckConstraint(
            "unlinked_at IS NULL OR unlinked_at >= linked_at",
            name="ck_whatsapp_conversation_opportunities_unlinked_after_linked",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["whatsapp_conversations.id"],
            name="fk_wa_conversation_opps_conversation",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
            name="fk_wa_conversation_opps_opportunity",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["linked_by_user_id"],
            ["users.id"],
            name="fk_wa_conversation_opps_linked_by_user",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_whatsapp_conversation_opportunities_active",
        "whatsapp_conversation_opportunities",
        ["conversation_id"],
        unique=True,
        postgresql_where=sa.text("unlinked_at IS NULL"),
    )
    op.create_index(
        "ix_whatsapp_conversation_opportunities_opportunity",
        "whatsapp_conversation_opportunities",
        ["opportunity_id"],
        unique=False,
    )

    op.create_table(
        "whatsapp_attachments",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("provider_media_id", sa.Text(), nullable=True),
        sa.Column("media_type", message_type_enum, nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=True),
        sa.Column("filename", sa.Text(), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column(
            "storage_status",
            storage_status_enum,
            server_default=sa.text("'PENDING'"),
            nullable=False,
        ),
        sa.Column("storage_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "media_type IN ('IMAGE', 'DOCUMENT')",
            name="ck_whatsapp_attachments_supported_type",
        ),
        sa.CheckConstraint(
            "provider_media_id IS NULL OR btrim(provider_media_id) <> ''",
            name="ck_whatsapp_attachments_provider_media_id_not_blank",
        ),
        sa.CheckConstraint(
            "mime_type IS NULL OR btrim(mime_type) <> ''",
            name="ck_whatsapp_attachments_mime_not_blank",
        ),
        sa.CheckConstraint(
            "filename IS NULL OR btrim(filename) <> ''",
            name="ck_whatsapp_attachments_filename_not_blank",
        ),
        sa.CheckConstraint(
            "size_bytes IS NULL OR size_bytes >= 0",
            name="ck_whatsapp_attachments_size_nonnegative",
        ),
        sa.CheckConstraint(
            "(storage_status = 'AVAILABLE' AND storage_key IS NOT NULL "
            "AND btrim(storage_key) <> '') OR storage_status <> 'AVAILABLE'",
            name="ck_whatsapp_attachments_available_has_key",
        ),
        sa.CheckConstraint(
            "storage_error IS NULL OR btrim(storage_error) <> ''",
            name="ck_whatsapp_attachments_storage_error_not_blank",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_whatsapp_attachments_updated_after_created",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["whatsapp_messages.id"],
            name="fk_whatsapp_attachments_message_id_messages",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_whatsapp_attachments_message",
        "whatsapp_attachments",
        ["message_id"],
        unique=True,
    )

    op.create_table(
        "whatsapp_message_status_events",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("external_message_id", sa.Text(), nullable=False),
        sa.Column("provider_state", provider_state_enum, nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("provider_error_code", sa.Text(), nullable=True),
        sa.Column("provider_error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "btrim(external_message_id) <> ''",
            name="ck_whatsapp_status_events_external_id_not_blank",
        ),
        sa.CheckConstraint(
            "provider_state <> 'RECEIVED'",
            name="ck_whatsapp_status_events_outbound_state",
        ),
        sa.CheckConstraint(
            "provider_error_code IS NULL OR btrim(provider_error_code) <> ''",
            name="ck_whatsapp_status_events_error_code_not_blank",
        ),
        sa.CheckConstraint(
            "provider_error_message IS NULL OR btrim(provider_error_message) <> ''",
            name="ck_whatsapp_status_events_error_message_not_blank",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["whatsapp_messages.id"],
            name="fk_whatsapp_status_events_message_id_messages",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "external_message_id",
            "provider_state",
            "occurred_at",
            name="uq_whatsapp_status_events_external_state_time",
        ),
    )
    op.create_index(
        "ix_whatsapp_status_events_unmatched_external",
        "whatsapp_message_status_events",
        ["external_message_id"],
        unique=False,
        postgresql_where=sa.text("message_id IS NULL"),
    )
    op.create_index(
        "ix_whatsapp_status_events_message_occurred",
        "whatsapp_message_status_events",
        ["message_id", "occurred_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_whatsapp_status_events_message_occurred",
        table_name="whatsapp_message_status_events",
    )
    op.drop_index(
        "ix_whatsapp_status_events_unmatched_external",
        table_name="whatsapp_message_status_events",
    )
    op.drop_table("whatsapp_message_status_events")

    op.drop_index(
        "uq_whatsapp_attachments_message",
        table_name="whatsapp_attachments",
    )
    op.drop_table("whatsapp_attachments")

    op.drop_index(
        "ix_whatsapp_conversation_opportunities_opportunity",
        table_name="whatsapp_conversation_opportunities",
    )
    op.drop_index(
        "uq_whatsapp_conversation_opportunities_active",
        table_name="whatsapp_conversation_opportunities",
    )
    op.drop_table("whatsapp_conversation_opportunities")

    op.drop_index(
        "ix_whatsapp_messages_conversation_updated",
        table_name="whatsapp_messages",
    )
    op.drop_index(
        "ix_whatsapp_messages_conversation_created",
        table_name="whatsapp_messages",
    )
    op.drop_index(
        "uq_whatsapp_messages_client_generated_id",
        table_name="whatsapp_messages",
    )
    op.drop_index(
        "uq_whatsapp_messages_external_id",
        table_name="whatsapp_messages",
    )
    op.drop_table("whatsapp_messages")

    op.drop_index(
        "ix_whatsapp_conversations_updated",
        table_name="whatsapp_conversations",
    )
    op.drop_index(
        "ix_whatsapp_conversations_customer",
        table_name="whatsapp_conversations",
    )
    op.drop_index(
        "ix_whatsapp_conversations_inbox",
        table_name="whatsapp_conversations",
    )
    op.drop_table("whatsapp_conversations")

    bind = op.get_bind()
    for enum_type in reversed(WHATSAPP_ENUMS):
        enum_type.drop(bind, checkfirst=False)
