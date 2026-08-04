from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Identity, Index, Text, func, text, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.opportunity_product import OpportunityProduct


class Product(TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("btrim(name) <> ''", name="ck_products_name_not_blank"),
        CheckConstraint(
            "updated_at >= created_at",
            name="ck_products_updated_after_created",
        ),
        Index(
            "uq_products_name_normalized",
            func.lower(func.btrim(text("name"))),
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=true(),
    )

    opportunity_products: Mapped[list[OpportunityProduct]] = relationship(
        back_populates="product",
        passive_deletes=True,
    )
