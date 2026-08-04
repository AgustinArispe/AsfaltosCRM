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

from app.db.base import Base, TimestampMixin
from app.models.enums import (
    LEAD_SOURCE_DB_ENUM,
    LOSS_REASON_DB_ENUM,
    OPPORTUNITY_STATUS_DB_ENUM,
    LeadSource,
    LossReason,
    OpportunityStatus,
)

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.opportunity_product import OpportunityProduct
    from app.models.opportunity_status_history import OpportunityStatusHistory
    from app.models.user import User


class Opportunity(TimestampMixin, Base):
    __tablename__ = "opportunities"
    __table_args__ = (
        CheckConstraint(
            "(status = 'PERDIDA' AND loss_reason IS NOT NULL) OR "
            "(status <> 'PERDIDA' AND loss_reason IS NULL)",
            name="ck_opportunities_loss_reason_matches_status",
        ),
        CheckConstraint(
            "current_status_entered_at >= created_at",
            name="ck_opportunities_status_entered_after_created",
        ),
        CheckConstraint(
            "updated_at >= created_at",
            name="ck_opportunities_updated_after_created",
        ),
        CheckConstraint(
            "deleted_at IS NULL OR deleted_at >= created_at",
            name="ck_opportunities_deleted_after_created",
        ),
        Index(
            "ix_opportunities_customer_created_at",
            "customer_id",
            text("created_at DESC"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_opportunities_status_entered_at",
            "status",
            "current_status_entered_at",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_opportunities_assignee_status",
            "assigned_user_id",
            "status",
            postgresql_where=text(
                "deleted_at IS NULL AND assigned_user_id IS NOT NULL"
            ),
        ),
        Index(
            "ix_opportunities_source_created_at",
            "source",
            "created_at",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_opportunities_legendary_wins",
            "customer_id",
            "current_status_entered_at",
            postgresql_where=text("status = 'GANADA' AND deleted_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "customers.id",
            name="fk_opportunities_customer_id_customers",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    assigned_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.id",
            name="fk_opportunities_assigned_user_id_users",
            ondelete="RESTRICT",
        ),
    )
    source: Mapped[LeadSource] = mapped_column(LEAD_SOURCE_DB_ENUM, nullable=False)
    status: Mapped[OpportunityStatus] = mapped_column(
        OPPORTUNITY_STATUS_DB_ENUM,
        nullable=False,
        server_default=OpportunityStatus.NUEVA.value,
    )
    loss_reason: Mapped[LossReason | None] = mapped_column(LOSS_REASON_DB_ENUM)
    current_status_entered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    customer: Mapped[Customer] = relationship(
        back_populates="opportunities",
        passive_deletes=True,
    )
    assigned_user: Mapped[User | None] = relationship(
        back_populates="assigned_opportunities",
        passive_deletes=True,
    )
    opportunity_products: Mapped[list[OpportunityProduct]] = relationship(
        back_populates="opportunity",
        passive_deletes=True,
    )
    status_history: Mapped[list[OpportunityStatusHistory]] = relationship(
        back_populates="opportunity",
        passive_deletes=True,
        order_by="OpportunityStatusHistory.changed_at",
    )
