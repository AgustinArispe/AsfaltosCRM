from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Identity,
    Index,
    Text,
    false,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.crm_commercial import CustomerLegendaryEvent
    from app.models.opportunity import Opportunity
    from app.models.whatsapp_conversation import WhatsAppConversation


class Customer(TimestampMixin, Base):
    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint("btrim(name) <> ''", name="ck_customers_name_not_blank"),
        CheckConstraint(
            "updated_at >= created_at",
            name="ck_customers_updated_after_created",
        ),
        CheckConstraint(
            "deleted_at IS NULL OR deleted_at >= created_at",
            name="ck_customers_deleted_after_created",
        ),
        Index(
            "ix_customers_name_normalized",
            func.lower(func.btrim(text("name"))),
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_customers_email_normalized",
            func.lower(func.btrim(text("email"))),
            postgresql_where=text("deleted_at IS NULL AND email IS NOT NULL"),
        ),
        Index(
            "ix_customers_phone_normalized",
            text("regexp_replace(phone, '[[:space:]()-]', '', 'g')"),
            postgresql_where=text("deleted_at IS NULL AND phone IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    company: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    province: Mapped[str | None] = mapped_column(Text)
    legendary_historical_override: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=false(),
    )
    legendary_automatic: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=false(),
    )
    legendary_automatic_evaluated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    opportunities: Mapped[list[Opportunity]] = relationship(
        back_populates="customer",
        passive_deletes=True,
    )
    whatsapp_conversations: Mapped[list[WhatsAppConversation]] = relationship(
        back_populates="customer",
        passive_deletes=True,
    )
    legendary_events: Mapped[list[CustomerLegendaryEvent]] = relationship(
        passive_deletes=True,
    )

    @property
    def is_legendary(self) -> bool:
        return self.legendary_historical_override or self.legendary_automatic
