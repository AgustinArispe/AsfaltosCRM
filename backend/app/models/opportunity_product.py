from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.opportunity import Opportunity
    from app.models.product import Product


class OpportunityProduct(TimestampMixin, Base):
    __tablename__ = "opportunity_products"
    __table_args__ = (
        CheckConstraint(
            "quantity_kg > 0",
            name="ck_opportunity_products_quantity_positive",
        ),
        CheckConstraint(
            "updated_at >= created_at",
            name="ck_opportunity_products_updated_after_created",
        ),
        Index(
            "ix_opportunity_products_product_opportunity",
            "product_id",
            "opportunity_id",
        ),
    )

    opportunity_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "opportunities.id",
            name="fk_opportunity_products_opportunity_id_opportunities",
            ondelete="RESTRICT",
        ),
        primary_key=True,
    )
    product_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "products.id",
            name="fk_opportunity_products_product_id_products",
            ondelete="RESTRICT",
        ),
        primary_key=True,
    )
    quantity_kg: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)

    opportunity: Mapped[Opportunity] = relationship(
        back_populates="opportunity_products",
        passive_deletes=True,
    )
    product: Mapped[Product] = relationship(
        back_populates="opportunity_products",
        passive_deletes=True,
    )
