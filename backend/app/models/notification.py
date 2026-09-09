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
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import NOTIFICATION_TYPE_DB_ENUM, NotificationType

if TYPE_CHECKING:
    from app.models.opportunity import Opportunity
    from app.models.user import User


class Notification(Base):
    """Persisted logical notification event shared by its recipients."""

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
    recipients: Mapped[list[NotificationRecipient]] = relationship(
        back_populates="notification",
        passive_deletes=True,
    )


class NotificationRecipient(Base):
    """Per-user delivery and read state for one logical notification."""

    __tablename__ = "notification_recipients"
    __table_args__ = (
        CheckConstraint(
            "read_at IS NULL OR read_at >= created_at",
            name="ck_notification_recipients_read_after_created",
        ),
        Index(
            "ix_notification_recipients_user_read",
            "user_id",
            "read_at",
        ),
        UniqueConstraint(
            "notification_id",
            "user_id",
            name="uq_notification_recipients_notification_user",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    notification_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "notifications.id",
            name="fk_notification_recipients_notification_id_notifications",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.id",
            name="fk_notification_recipients_user_id_users",
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

    notification: Mapped[Notification] = relationship(back_populates="recipients")
    user: Mapped[User] = relationship(back_populates="notification_recipients")
