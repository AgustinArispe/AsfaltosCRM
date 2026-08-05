from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import LEAD_SOURCE_DB_ENUM, LeadSource

if TYPE_CHECKING:
    from app.models.opportunity import Opportunity


class LeadIntake(Base):
    """Immutable snapshot of an accepted external lead submission."""

    __tablename__ = "lead_intakes"
    __table_args__ = (
        CheckConstraint(
            "btrim(external_submission_id) <> ''",
            name="ck_lead_intakes_external_id_not_blank",
        ),
        CheckConstraint(
            "btrim(submitted_name) <> ''",
            name="ck_lead_intakes_name_not_blank",
        ),
        CheckConstraint(
            "submitted_company IS NULL OR btrim(submitted_company) <> ''",
            name="ck_lead_intakes_company_not_blank",
        ),
        CheckConstraint(
            "submitted_email IS NULL OR btrim(submitted_email) <> ''",
            name="ck_lead_intakes_email_not_blank",
        ),
        CheckConstraint(
            "submitted_phone IS NULL OR btrim(submitted_phone) <> ''",
            name="ck_lead_intakes_phone_not_blank",
        ),
        CheckConstraint(
            "submitted_province IS NULL OR btrim(submitted_province) <> ''",
            name="ck_lead_intakes_province_not_blank",
        ),
        CheckConstraint(
            "message IS NULL OR btrim(message) <> ''",
            name="ck_lead_intakes_message_not_blank",
        ),
        UniqueConstraint(
            "source",
            "external_submission_id",
            name="uq_lead_intakes_source_external_id",
        ),
        UniqueConstraint(
            "opportunity_id",
            name="uq_lead_intakes_opportunity_id",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    source: Mapped[LeadSource] = mapped_column(LEAD_SOURCE_DB_ENUM, nullable=False)
    external_submission_id: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_name: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_company: Mapped[str | None] = mapped_column(Text)
    submitted_email: Mapped[str | None] = mapped_column(Text)
    submitted_phone: Mapped[str | None] = mapped_column(Text)
    submitted_province: Mapped[str | None] = mapped_column(Text)
    message: Mapped[str | None] = mapped_column(Text)
    opportunity_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "opportunities.id",
            name="fk_lead_intakes_opportunity_id_opportunities",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    opportunity: Mapped[Opportunity] = relationship(
        back_populates="lead_intake",
        passive_deletes=True,
    )
