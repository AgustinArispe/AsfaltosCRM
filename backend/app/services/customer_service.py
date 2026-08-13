from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.models import Customer
from app.services.errors import (
    DeletedCustomerError,
    EntityNotFoundError,
    StaleWriteConflictError,
)
from app.services.legendary_service import LegendaryService

CUSTOMER_UPDATE_FIELDS = frozenset(
    {
        "name",
        "company",
        "email",
        "phone",
        "province",
        "legendary_historical_override",
    }
)


class CustomerService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_customer(
        self,
        *,
        name: str,
        company: str | None,
        email: str | None,
        phone: str | None,
        province: str | None,
        legendary_historical_override: bool,
        actor_user_id: int | None = None,
    ) -> Customer:
        with self._session.begin():
            customer = Customer(
                name=name,
                company=company,
                email=email,
                phone=phone,
                province=province,
                legendary_historical_override=legendary_historical_override,
            )
            self._session.add(customer)
            self._session.flush()
            if legendary_historical_override:
                if actor_user_id is None:
                    raise ValueError("actor_user_id is required for a manual override")
                customer.legendary_historical_override = False
                LegendaryService(self._session).record_manual_change_in_transaction(
                    customer,
                    new_value=True,
                    actor_user_id=actor_user_id,
                    occurred_at=datetime.now(UTC),
                )
                self._session.flush()
        return customer

    def list_customers(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        include_deleted: bool,
    ) -> tuple[list[Customer], int]:
        filters: list[ColumnElement[bool]] = []
        if not include_deleted:
            filters.append(Customer.deleted_at.is_(None))
        if search:
            pattern = f"%{search.strip()}%"
            filters.append(
                or_(
                    Customer.name.ilike(pattern),
                    Customer.company.ilike(pattern),
                    Customer.email.ilike(pattern),
                    Customer.phone.ilike(pattern),
                )
            )

        total = self._session.scalar(
            select(func.count()).select_from(Customer).where(*filters)
        )
        customers = list(
            self._session.scalars(
                select(Customer)
                .where(*filters)
                .order_by(
                    func.lower(func.btrim(Customer.name)),
                    Customer.id,
                )
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return customers, total or 0

    def get_customer(self, customer_id: int) -> Customer:
        customer = self._session.scalar(
            select(Customer).where(
                Customer.id == customer_id,
                Customer.deleted_at.is_(None),
            )
        )
        if customer is None:
            raise EntityNotFoundError("Customer", customer_id)
        return customer

    def update_customer(
        self,
        customer_id: int,
        updates: dict[str, str | bool | None],
        *,
        expected_updated_at: datetime | None = None,
        actor_user_id: int | None = None,
    ) -> Customer:
        with self._session.begin():
            customer = self._session.scalar(
                select(Customer).where(Customer.id == customer_id).with_for_update()
            )
            if customer is None:
                raise EntityNotFoundError("Customer", customer_id)
            if customer.deleted_at is not None:
                raise DeletedCustomerError(customer_id)
            if (
                expected_updated_at is not None
                and customer.updated_at != expected_updated_at
            ):
                raise StaleWriteConflictError(
                    resource="Customer",
                    current_updated_at=customer.updated_at,
                )

            manual_value = updates.get("legendary_historical_override")
            for field_name, value in updates.items():
                if field_name in CUSTOMER_UPDATE_FIELDS:
                    if field_name == "legendary_historical_override":
                        continue
                    setattr(customer, field_name, value)
            if isinstance(manual_value, bool):
                if actor_user_id is None:
                    raise ValueError("actor_user_id is required for a manual override")
                LegendaryService(self._session).record_manual_change_in_transaction(
                    customer,
                    new_value=manual_value,
                    actor_user_id=actor_user_id,
                    occurred_at=datetime.now(UTC),
                )
            if updates:
                customer.updated_at = datetime.now(UTC)
            self._session.flush()
        return customer

    def soft_delete_customer(self, customer_id: int) -> None:
        with self._session.begin():
            customer = self._session.scalar(
                select(Customer).where(Customer.id == customer_id).with_for_update()
            )
            if customer is None:
                raise EntityNotFoundError("Customer", customer_id)
            if customer.deleted_at is None:
                deleted_at = datetime.now(UTC)
                customer.deleted_at = deleted_at
                customer.updated_at = deleted_at
                self._session.flush()
