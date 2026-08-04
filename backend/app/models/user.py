from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Identity, Index, Text, func, text, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import USER_ROLE_DB_ENUM, UserRole

if TYPE_CHECKING:
    from app.models.opportunity import Opportunity
    from app.models.opportunity_status_history import OpportunityStatusHistory


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("btrim(full_name) <> ''", name="ck_users_full_name_not_blank"),
        CheckConstraint("btrim(email) <> ''", name="ck_users_email_not_blank"),
        CheckConstraint(
            "btrim(password_hash) <> ''",
            name="ck_users_password_hash_not_blank",
        ),
        CheckConstraint(
            "updated_at >= created_at",
            name="ck_users_updated_after_created",
        ),
        Index(
            "uq_users_email_normalized",
            func.lower(func.btrim(text("email"))),
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[UserRole] = mapped_column(USER_ROLE_DB_ENUM, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=true(),
    )

    assigned_opportunities: Mapped[list[Opportunity]] = relationship(
        back_populates="assigned_user",
        passive_deletes=True,
    )
    status_changes: Mapped[list[OpportunityStatusHistory]] = relationship(
        back_populates="changed_by_user",
        passive_deletes=True,
    )
