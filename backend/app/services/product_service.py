from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.integrity import violates_constraint
from app.models import Product
from app.services.errors import DuplicateEntityError, EntityNotFoundError

PRODUCT_UPDATE_FIELDS = frozenset({"name", "is_active"})


class ProductService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_products(self, *, include_inactive: bool) -> list[Product]:
        statement = select(Product)
        if not include_inactive:
            statement = statement.where(Product.is_active.is_(True))
        return list(
            self._session.scalars(
                statement.order_by(
                    func.lower(func.btrim(Product.name)),
                    Product.id,
                )
            )
        )

    def create_product(self, *, name: str) -> Product:
        try:
            with self._session.begin():
                product = Product(name=name)
                self._session.add(product)
                self._session.flush()
        except IntegrityError as error:
            if not violates_constraint(error, "uq_products_name_normalized"):
                raise
            raise DuplicateEntityError("Product", "name") from error
        return product

    def update_product(
        self,
        product_id: int,
        updates: dict[str, str | bool | None],
    ) -> Product:
        try:
            with self._session.begin():
                product = self._session.scalar(
                    select(Product).where(Product.id == product_id).with_for_update()
                )
                if product is None:
                    raise EntityNotFoundError("Product", product_id)

                for field_name, value in updates.items():
                    if field_name in PRODUCT_UPDATE_FIELDS:
                        setattr(product, field_name, value)
                if updates:
                    product.updated_at = datetime.now(UTC)
                self._session.flush()
        except IntegrityError as error:
            if not violates_constraint(error, "uq_products_name_normalized"):
                raise
            raise DuplicateEntityError("Product", "name") from error
        return product
