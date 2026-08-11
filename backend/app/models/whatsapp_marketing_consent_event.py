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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    WHATSAPP_CONSENT_DECISION_DB_ENUM,
    WHATSAPP_CONSENT_SOURCE_DB_ENUM,
    WhatsAppConsentDecision,
    WhatsAppConsentSource,
)

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.user import User


class WhatsAppMarketingConsentEvent(Base):
    __tablename__ = "whatsapp_marketing_consent_events"
    __table_args__ = (
        CheckConstraint(
            "btrim(normalized_phone) <> ''",
            name="ck_whatsapp_consent_events_phone_not_blank",
        ),
        CheckConstraint(
            "evidence_reference IS NULL OR btrim(evidence_reference) <> ''",
            name="ck_whatsapp_consent_events_evidence_not_blank",
        ),
        CheckConstraint(
            "source <> 'EXTERNAL_FAA' OR evidence_reference IS NOT NULL",
            name="ck_whatsapp_consent_events_external_evidence",
        ),
        CheckConstraint(
            "effective_at <= recorded_at",
            name="ck_whatsapp_consent_events_not_future",
        ),
        Index(
            "uq_whatsapp_consent_events_client_id",
            "client_event_id",
            unique=True,
        ),
        Index(
            "ix_whatsapp_consent_events_current",
            "customer_id",
            "normalized_phone",
            "effective_at",
            "id",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    client_event_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    customer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "customers.id",
            name="fk_whatsapp_consent_events_customer_id_customers",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    normalized_phone: Mapped[str] = mapped_column(Text, nullable=False)
    decision: Mapped[WhatsAppConsentDecision] = mapped_column(
        WHATSAPP_CONSENT_DECISION_DB_ENUM,
        nullable=False,
    )
    source: Mapped[WhatsAppConsentSource] = mapped_column(
        WHATSAPP_CONSENT_SOURCE_DB_ENUM,
        nullable=False,
    )
    evidence_reference: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    effective_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    recorded_by_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.id",
            name="fk_whatsapp_consent_events_recorded_by_users",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    customer: Mapped[Customer] = relationship(passive_deletes=True)
    recorded_by_user: Mapped[User] = relationship(passive_deletes=True)
