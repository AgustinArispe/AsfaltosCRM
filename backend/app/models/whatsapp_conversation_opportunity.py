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
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    WHATSAPP_OPPORTUNITY_LINK_SOURCE_DB_ENUM,
    WhatsAppOpportunityLinkSource,
)

if TYPE_CHECKING:
    from app.models.opportunity import Opportunity
    from app.models.user import User
    from app.models.whatsapp_conversation import WhatsAppConversation


class WhatsAppConversationOpportunity(Base):
    __tablename__ = "whatsapp_conversation_opportunities"
    __table_args__ = (
        CheckConstraint(
            "unlinked_at IS NULL OR unlinked_at >= linked_at",
            name="ck_whatsapp_conversation_opportunities_unlinked_after_linked",
        ),
        Index(
            "uq_whatsapp_conversation_opportunities_active",
            "conversation_id",
            unique=True,
            postgresql_where=text("unlinked_at IS NULL"),
        ),
        Index(
            "ix_whatsapp_conversation_opportunities_opportunity",
            "opportunity_id",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "whatsapp_conversations.id",
            name="fk_wa_conversation_opps_conversation",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    opportunity_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "opportunities.id",
            name="fk_wa_conversation_opps_opportunity",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    unlinked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    linked_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.id",
            name="fk_wa_conversation_opps_linked_by_user",
            ondelete="RESTRICT",
        ),
    )
    link_source: Mapped[WhatsAppOpportunityLinkSource] = mapped_column(
        WHATSAPP_OPPORTUNITY_LINK_SOURCE_DB_ENUM,
        nullable=False,
    )

    conversation: Mapped[WhatsAppConversation] = relationship(
        back_populates="opportunity_links",
        passive_deletes=True,
    )
    opportunity: Mapped[Opportunity] = relationship(
        back_populates="whatsapp_conversation_links",
        passive_deletes=True,
    )
    linked_by_user: Mapped[User | None] = relationship(
        back_populates="whatsapp_opportunity_links",
        passive_deletes=True,
    )
