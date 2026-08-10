from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    false,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import (
    WHATSAPP_CONVERSATION_RESOLUTION_DB_ENUM,
    WhatsAppConversationResolution,
)
from app.models.whatsapp_conversation_opportunity import (
    WhatsAppConversationOpportunity,
)
from app.models.whatsapp_message import WhatsAppMessage

if TYPE_CHECKING:
    from app.models.customer import Customer


class WhatsAppConversation(TimestampMixin, Base):
    __tablename__ = "whatsapp_conversations"
    __table_args__ = (
        CheckConstraint(
            "btrim(external_phone) <> ''",
            name="ck_whatsapp_conversations_phone_not_blank",
        ),
        CheckConstraint(
            "btrim(phone_match_key) <> ''",
            name="ck_whatsapp_conversations_phone_key_not_blank",
        ),
        CheckConstraint(
            "display_name IS NULL OR btrim(display_name) <> ''",
            name="ck_whatsapp_conversations_display_name_not_blank",
        ),
        CheckConstraint(
            "customer_id IS NOT NULL OR resolution_status = 'NEEDS_REVIEW'",
            name="ck_whatsapp_conversations_unresolved_customer",
        ),
        CheckConstraint(
            "unread_count >= 0",
            name="ck_whatsapp_conversations_unread_nonnegative",
        ),
        CheckConstraint(
            "(waiting_for_response AND waiting_since_at IS NOT NULL) OR "
            "(NOT waiting_for_response AND waiting_since_at IS NULL)",
            name="ck_whatsapp_conversations_waiting_matches_since",
        ),
        CheckConstraint(
            "updated_at >= created_at",
            name="ck_whatsapp_conversations_updated_after_created",
        ),
        UniqueConstraint(
            "phone_match_key",
            name="uq_whatsapp_conversations_phone_match_key",
        ),
        Index(
            "ix_whatsapp_conversations_inbox",
            text("waiting_for_response DESC"),
            text("unread_count DESC"),
            text("last_message_at DESC"),
            text("id DESC"),
        ),
        Index(
            "ix_whatsapp_conversations_customer",
            "customer_id",
        ),
        Index(
            "ix_whatsapp_conversations_updated",
            "updated_at",
            "id",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    customer_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "customers.id",
            name="fk_whatsapp_conversations_customer_id_customers",
            ondelete="RESTRICT",
        ),
    )
    external_phone: Mapped[str] = mapped_column(Text, nullable=False)
    phone_match_key: Mapped[str] = mapped_column(Text, nullable=False)
    provider_contact_id: Mapped[str | None] = mapped_column(Text)
    display_name: Mapped[str | None] = mapped_column(Text)
    resolution_status: Mapped[WhatsAppConversationResolution] = mapped_column(
        WHATSAPP_CONVERSATION_RESOLUTION_DB_ENUM,
        nullable=False,
    )
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_inbound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_outbound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    unread_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    waiting_for_response: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=false(),
    )
    waiting_since_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    window_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    customer: Mapped[Customer | None] = relationship(
        back_populates="whatsapp_conversations",
        passive_deletes=True,
    )
    messages: Mapped[list[WhatsAppMessage]] = relationship(
        back_populates="conversation",
        passive_deletes=True,
        order_by=lambda: (WhatsAppMessage.created_at, WhatsAppMessage.id),
    )
    opportunity_links: Mapped[list[WhatsAppConversationOpportunity]] = relationship(
        back_populates="conversation",
        passive_deletes=True,
        order_by=lambda: (
            WhatsAppConversationOpportunity.linked_at,
            WhatsAppConversationOpportunity.id,
        ),
    )
