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
from app.models.enums import NOTIFICATION_TYPE_DB_ENUM, NotificationType

if TYPE_CHECKING:
    from app.models.opportunity import Opportunity


class Notification(Base):
    """Persisted global operational notification."""

    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "read_at IS NULL OR read_at >= created_at",
            name="ck_notifications_read_after_created",
        ),
        CheckConstraint(
            "resolved_at IS NULL OR resolved_at >= created_at",
            name="ck_notifications_resolved_after_created",
        ),
        Index(
            "uq_notifications_active_type_opportunity",
            "opportunity_id",
            "type",
            unique=True,
            postgresql_where=text("resolved_at IS NULL"),
        ),
        Index(
            "ix_notifications_active_created_at",
            text("created_at DESC"),
            text("id DESC"),
            postgresql_where=text("resolved_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    type: Mapped[NotificationType] = mapped_column(
        NOTIFICATION_TYPE_DB_ENUM,
        nullable=False,
    )
    opportunity_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "opportunities.id",
            name="fk_notifications_opportunity_id_opportunities",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    opportunity: Mapped[Opportunity] = relationship(
        back_populates="notifications",
        passive_deletes=True,
    )
