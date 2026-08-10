from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    WHATSAPP_PROVIDER_STATE_DB_ENUM,
    WhatsAppProviderState,
)

if TYPE_CHECKING:
    from app.models.whatsapp_message import WhatsAppMessage


class WhatsAppMessageStatusEvent(Base):
    __tablename__ = "whatsapp_message_status_events"
    __table_args__ = (
        CheckConstraint(
            "btrim(external_message_id) <> ''",
            name="ck_whatsapp_status_events_external_id_not_blank",
        ),
        CheckConstraint(
            "provider_state <> 'RECEIVED'",
            name="ck_whatsapp_status_events_outbound_state",
        ),
        CheckConstraint(
            "provider_error_code IS NULL OR btrim(provider_error_code) <> ''",
            name="ck_whatsapp_status_events_error_code_not_blank",
        ),
        CheckConstraint(
            "provider_error_message IS NULL OR btrim(provider_error_message) <> ''",
            name="ck_whatsapp_status_events_error_message_not_blank",
        ),
        UniqueConstraint(
            "external_message_id",
            "provider_state",
            "occurred_at",
            name="uq_whatsapp_status_events_external_state_time",
        ),
        Index(
            "ix_whatsapp_status_events_unmatched_external",
            "external_message_id",
            postgresql_where=text("message_id IS NULL"),
        ),
        Index(
            "ix_whatsapp_status_events_message_occurred",
            "message_id",
            "occurred_at",
            "id",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    message_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "whatsapp_messages.id",
            name="fk_whatsapp_status_events_message_id_messages",
            ondelete="RESTRICT",
        ),
    )
    external_message_id: Mapped[str] = mapped_column(Text, nullable=False)
    provider_state: Mapped[WhatsAppProviderState] = mapped_column(
        WHATSAPP_PROVIDER_STATE_DB_ENUM,
        nullable=False,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    provider_error_code: Mapped[str | None] = mapped_column(Text)
    provider_error_message: Mapped[str | None] = mapped_column(Text)

    message: Mapped[WhatsAppMessage | None] = relationship(
        back_populates="status_events",
        passive_deletes=True,
    )
