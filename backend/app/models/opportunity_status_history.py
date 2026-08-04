from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Identity, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import OPPORTUNITY_STATUS_DB_ENUM, OpportunityStatus

if TYPE_CHECKING:
    from app.models.opportunity import Opportunity
    from app.models.user import User


class OpportunityStatusHistory(Base):
    __tablename__ = "opportunity_status_history"
    __table_args__ = (
        CheckConstraint(
            "from_status IS NOT NULL OR to_status = 'NUEVA'",
            name="ck_status_history_creation_starts_new",
        ),
        Index(
            "ix_status_history_opportunity_changed_at",
            "opportunity_id",
            "changed_at",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "opportunities.id",
            name="fk_status_history_opportunity_id_opportunities",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    from_status: Mapped[OpportunityStatus | None] = mapped_column(
        OPPORTUNITY_STATUS_DB_ENUM
    )
    to_status: Mapped[OpportunityStatus] = mapped_column(
        OPPORTUNITY_STATUS_DB_ENUM,
        nullable=False,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    changed_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.id",
            name="fk_status_history_changed_by_user_id_users",
            ondelete="RESTRICT",
        ),
    )

    opportunity: Mapped[Opportunity] = relationship(
        back_populates="status_history",
        passive_deletes=True,
    )
    changed_by_user: Mapped[User | None] = relationship(
        back_populates="status_changes",
        passive_deletes=True,
    )
