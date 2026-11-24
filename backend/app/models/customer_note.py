from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Text,
    Uuid,
    false,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class CustomerNote(TimestampMixin, Base):
    __tablename__ = "customer_notes"
    __table_args__ = (
        CheckConstraint(
            "btrim(body) <> '' AND char_length(body) <= 600",
            name="ck_customer_notes_body",
        ),
        Index(
            "ix_customer_notes_active",
            "customer_id",
            "pinned",
            "id",
            postgresql_where=text("archived_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False
    )
    author_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    command_id: Mapped[UUID | None] = mapped_column(Uuid, unique=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    pinned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=false()
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    author: Mapped[User] = relationship()

    @property
    def author_name(self) -> str:
        return self.author.full_name
