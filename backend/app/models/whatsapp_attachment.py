from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Identity,
    Index,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import (
    WHATSAPP_MESSAGE_TYPE_DB_ENUM,
    WHATSAPP_STORAGE_STATUS_DB_ENUM,
    WhatsAppMessageType,
    WhatsAppStorageStatus,
)

if TYPE_CHECKING:
    from app.models.whatsapp_message import WhatsAppMessage


class WhatsAppAttachment(TimestampMixin, Base):
    __tablename__ = "whatsapp_attachments"
    __table_args__ = (
        CheckConstraint(
            "media_type IN ('IMAGE', 'DOCUMENT')",
            name="ck_whatsapp_attachments_supported_type",
        ),
        CheckConstraint(
            "provider_media_id IS NULL OR btrim(provider_media_id) <> ''",
            name="ck_whatsapp_attachments_provider_media_id_not_blank",
        ),
        CheckConstraint(
            "mime_type IS NULL OR btrim(mime_type) <> ''",
            name="ck_whatsapp_attachments_mime_not_blank",
        ),
        CheckConstraint(
            "filename IS NULL OR btrim(filename) <> ''",
            name="ck_whatsapp_attachments_filename_not_blank",
        ),
        CheckConstraint(
            "size_bytes IS NULL OR size_bytes >= 0",
            name="ck_whatsapp_attachments_size_nonnegative",
        ),
        CheckConstraint(
            "(storage_status = 'AVAILABLE' AND storage_key IS NOT NULL "
            "AND btrim(storage_key) <> '') OR storage_status <> 'AVAILABLE'",
            name="ck_whatsapp_attachments_available_has_key",
        ),
        CheckConstraint(
            "storage_error IS NULL OR btrim(storage_error) <> ''",
            name="ck_whatsapp_attachments_storage_error_not_blank",
        ),
        CheckConstraint(
            "updated_at >= created_at",
            name="ck_whatsapp_attachments_updated_after_created",
        ),
        Index(
            "uq_whatsapp_attachments_message",
            "message_id",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    message_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "whatsapp_messages.id",
            name="fk_whatsapp_attachments_message_id_messages",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    provider_media_id: Mapped[str | None] = mapped_column(Text)
    media_type: Mapped[WhatsAppMessageType] = mapped_column(
        WHATSAPP_MESSAGE_TYPE_DB_ENUM,
        nullable=False,
    )
    mime_type: Mapped[str | None] = mapped_column(Text)
    filename: Mapped[str | None] = mapped_column(Text)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    storage_key: Mapped[str | None] = mapped_column(Text)
    storage_status: Mapped[WhatsAppStorageStatus] = mapped_column(
        WHATSAPP_STORAGE_STATUS_DB_ENUM,
        nullable=False,
        server_default=WhatsAppStorageStatus.PENDING.value,
    )
    storage_error: Mapped[str | None] = mapped_column(Text)

    message: Mapped[WhatsAppMessage] = relationship(
        back_populates="attachment",
        passive_deletes=True,
    )
