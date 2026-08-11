from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import (
    WHATSAPP_DIRECTION_DB_ENUM,
    WHATSAPP_DISPATCH_STATE_DB_ENUM,
    WHATSAPP_MESSAGE_ORIGIN_DB_ENUM,
    WHATSAPP_MESSAGE_TYPE_DB_ENUM,
    WHATSAPP_PROVIDER_STATE_DB_ENUM,
    WhatsAppDirection,
    WhatsAppDispatchState,
    WhatsAppMessageOrigin,
    WhatsAppMessageType,
    WhatsAppProviderState,
)
from app.models.whatsapp_message_status_event import WhatsAppMessageStatusEvent

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.whatsapp_attachment import WhatsAppAttachment
    from app.models.whatsapp_broadcast import WhatsAppBroadcastRecipient
    from app.models.whatsapp_conversation import WhatsAppConversation


class WhatsAppMessage(TimestampMixin, Base):
    __tablename__ = "whatsapp_messages"
    __table_args__ = (
        CheckConstraint(
            "external_message_id IS NULL OR btrim(external_message_id) <> ''",
            name="ck_whatsapp_messages_external_id_not_blank",
        ),
        CheckConstraint(
            "(direction = 'INBOUND' AND external_message_id IS NOT NULL "
            "AND client_generated_id IS NULL AND dispatch_state IS NULL "
            "AND provider_state = 'RECEIVED' AND sent_by_user_id IS NULL) OR "
            "(direction = 'OUTBOUND' AND client_generated_id IS NOT NULL "
            "AND dispatch_state IS NOT NULL "
            "AND (provider_state IS NULL OR provider_state <> 'RECEIVED') "
            "AND sent_by_user_id IS NOT NULL)",
            name="ck_whatsapp_messages_direction_contract",
        ),
        CheckConstraint(
            "message_type <> 'TEXT' OR origin = 'BROADCAST' "
            "OR (body IS NOT NULL AND btrim(body) <> '')",
            name="ck_whatsapp_messages_text_body",
        ),
        CheckConstraint(
            "(origin = 'HUMAN' AND broadcast_recipient_id IS NULL "
            "AND template_name IS NULL AND template_language IS NULL) OR "
            "(origin = 'BROADCAST' AND direction = 'OUTBOUND' "
            "AND broadcast_recipient_id IS NOT NULL "
            "AND template_name IS NOT NULL AND template_language IS NOT NULL)",
            name="ck_whatsapp_messages_origin_contract",
        ),
        CheckConstraint(
            "provider_error_code IS NULL OR btrim(provider_error_code) <> ''",
            name="ck_whatsapp_messages_error_code_not_blank",
        ),
        CheckConstraint(
            "provider_error_message IS NULL OR btrim(provider_error_message) <> ''",
            name="ck_whatsapp_messages_error_message_not_blank",
        ),
        CheckConstraint(
            "updated_at >= created_at",
            name="ck_whatsapp_messages_updated_after_created",
        ),
        Index(
            "uq_whatsapp_messages_external_id",
            "external_message_id",
            unique=True,
            postgresql_where=text("external_message_id IS NOT NULL"),
        ),
        Index(
            "uq_whatsapp_messages_client_generated_id",
            "client_generated_id",
            unique=True,
            postgresql_where=text("client_generated_id IS NOT NULL"),
        ),
        Index(
            "ix_whatsapp_messages_conversation_created",
            "conversation_id",
            "created_at",
            "id",
        ),
        Index(
            "uq_whatsapp_messages_broadcast_initial",
            "broadcast_recipient_id",
            unique=True,
            postgresql_where=text(
                "broadcast_recipient_id IS NOT NULL AND retry_of_message_id IS NULL"
            ),
        ),
        Index(
            "ix_whatsapp_messages_conversation_updated",
            "conversation_id",
            "updated_at",
            "id",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "whatsapp_conversations.id",
            name="fk_whatsapp_messages_conversation_id_conversations",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    external_message_id: Mapped[str | None] = mapped_column(Text)
    client_generated_id: Mapped[UUID | None] = mapped_column(Uuid)
    direction: Mapped[WhatsAppDirection] = mapped_column(
        WHATSAPP_DIRECTION_DB_ENUM,
        nullable=False,
    )
    message_type: Mapped[WhatsAppMessageType] = mapped_column(
        WHATSAPP_MESSAGE_TYPE_DB_ENUM,
        nullable=False,
    )
    origin: Mapped[WhatsAppMessageOrigin] = mapped_column(
        WHATSAPP_MESSAGE_ORIGIN_DB_ENUM,
        nullable=False,
        default=WhatsAppMessageOrigin.HUMAN,
        server_default=WhatsAppMessageOrigin.HUMAN.value,
    )
    body: Mapped[str | None] = mapped_column(Text)
    sent_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.id",
            name="fk_whatsapp_messages_sent_by_user_id_users",
            ondelete="RESTRICT",
        ),
    )
    retry_of_message_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "whatsapp_messages.id",
            name="fk_whatsapp_messages_retry_of_message_id_messages",
            ondelete="RESTRICT",
        ),
    )
    broadcast_recipient_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "whatsapp_broadcast_recipients.id",
            name="fk_whatsapp_messages_broadcast_recipient_id_recipients",
            ondelete="RESTRICT",
        ),
    )
    template_name: Mapped[str | None] = mapped_column(Text)
    template_language: Mapped[str | None] = mapped_column(Text)
    dispatch_state: Mapped[WhatsAppDispatchState | None] = mapped_column(
        WHATSAPP_DISPATCH_STATE_DB_ENUM
    )
    provider_state: Mapped[WhatsAppProviderState | None] = mapped_column(
        WHATSAPP_PROVIDER_STATE_DB_ENUM
    )
    provider_error_code: Mapped[str | None] = mapped_column(Text)
    provider_error_message: Mapped[str | None] = mapped_column(Text)
    provider_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_status_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    conversation: Mapped[WhatsAppConversation] = relationship(
        back_populates="messages",
        passive_deletes=True,
    )
    sent_by_user: Mapped[User | None] = relationship(
        back_populates="whatsapp_messages",
        passive_deletes=True,
    )
    retry_of_message: Mapped[WhatsAppMessage | None] = relationship(
        remote_side=lambda: WhatsAppMessage.id,
        passive_deletes=True,
    )
    broadcast_recipient: Mapped[WhatsAppBroadcastRecipient | None] = relationship(
        back_populates="messages",
        passive_deletes=True,
    )
    attachment: Mapped[WhatsAppAttachment | None] = relationship(
        back_populates="message",
        passive_deletes=True,
        uselist=False,
    )
    status_events: Mapped[list[WhatsAppMessageStatusEvent]] = relationship(
        back_populates="message",
        passive_deletes=True,
        order_by=lambda: (
            WhatsAppMessageStatusEvent.occurred_at,
            WhatsAppMessageStatusEvent.id,
        ),
    )
