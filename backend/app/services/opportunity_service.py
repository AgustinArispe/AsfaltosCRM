from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Customer,
    LeadSource,
    LossReason,
    Opportunity,
    OpportunityProduct,
    OpportunityStatus,
    OpportunityStatusHistory,
    Product,
    User,
)
from app.services.errors import (
    ClosedOpportunityError,
    DeletedCustomerError,
    EntityNotFoundError,
    InactiveProductError,
    InactiveUserError,
    InvalidLossReasonError,
    InvalidQuoteProductsError,
    InvalidStateTransitionError,
)
from app.services.notification_service import NotificationService

TERMINAL_STATUSES = frozenset({OpportunityStatus.GANADA, OpportunityStatus.PERDIDA})


@dataclass(frozen=True, slots=True)
class QuoteProductInput:
    product_id: int
    quantity_kg: Decimal


class OpportunityService:
    """Coordinates atomic opportunity operations and their business rules.

    Each public method owns one transaction. Callers should provide a Session with no
    active transaction; the method commits on success and rolls back on any exception.
    Opportunity mutations use a row lock so simultaneous requests cannot both apply a
    transition based on the same stale status.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_opportunity(
        self,
        *,
        customer_id: int,
        source: LeadSource,
        assigned_user_id: int | None = None,
        changed_by_user_id: int | None = None,
    ) -> Opportunity:
        with self._session.begin():
            return self.create_opportunity_in_transaction(
                customer_id=customer_id,
                source=source,
                assigned_user_id=assigned_user_id,
                changed_by_user_id=changed_by_user_id,
            )

    def create_opportunity_in_transaction(
        self,
        *,
        customer_id: int,
        source: LeadSource,
        assigned_user_id: int | None = None,
        changed_by_user_id: int | None = None,
    ) -> Opportunity:
        """Create NUEVA plus its history inside a caller-owned transaction.

        This explicit composable operation never begins or commits a transaction. It
        exists for application services, such as Lead Intake, that must combine the
        opportunity creation with other writes atomically.
        """
        self._get_available_customer(customer_id)
        self._validate_assigned_user(assigned_user_id)
        self._validate_history_user(changed_by_user_id)

        opportunity = Opportunity(
            customer_id=customer_id,
            assigned_user_id=assigned_user_id,
            source=source,
            status=OpportunityStatus.NUEVA,
            loss_reason=None,
        )
        self._session.add(opportunity)
        self._session.flush()
        self._add_history(
            opportunity=opportunity,
            from_status=None,
            to_status=OpportunityStatus.NUEVA,
            changed_at=opportunity.current_status_entered_at,
            changed_by_user_id=changed_by_user_id,
        )
        self._session.flush()
        return opportunity

    def quote_opportunity(
        self,
        opportunity_id: int,
        products: list[QuoteProductInput],
        *,
        changed_by_user_id: int | None = None,
    ) -> Opportunity:
        with self._session.begin():
            opportunity = self._get_opportunity_for_update(opportunity_id)
            self._require_transition(
                opportunity,
                expected_status=OpportunityStatus.NUEVA,
                target_status=OpportunityStatus.COTIZADA,
            )
            self._validate_history_user(changed_by_user_id)
            validated_products = self._validate_quote_products(
                products,
                existing_product_ids=frozenset(),
            )
            self._replace_quote_products(opportunity.id, validated_products)
            self._transition(
                opportunity,
                to_status=OpportunityStatus.COTIZADA,
                changed_by_user_id=changed_by_user_id,
            )
            self._session.flush()

        return opportunity

    def move_to_negotiation(
        self,
        opportunity_id: int,
        *,
        changed_by_user_id: int | None = None,
    ) -> Opportunity:
        with self._session.begin():
            opportunity = self._get_opportunity_for_update(opportunity_id)
            self._require_transition(
                opportunity,
                expected_status=OpportunityStatus.COTIZADA,
                target_status=OpportunityStatus.NEGOCIACION,
            )
            self._validate_history_user(changed_by_user_id)
            self._require_quoted_products(opportunity.id)
            self._transition(
                opportunity,
                to_status=OpportunityStatus.NEGOCIACION,
                changed_by_user_id=changed_by_user_id,
            )
            self._session.flush()

        return opportunity

    def mark_as_won(
        self,
        opportunity_id: int,
        *,
        changed_by_user_id: int | None = None,
    ) -> Opportunity:
        with self._session.begin():
            opportunity = self._get_opportunity_for_update(opportunity_id)
            self._require_transition(
                opportunity,
                expected_status=OpportunityStatus.NEGOCIACION,
                target_status=OpportunityStatus.GANADA,
            )
            self._validate_history_user(changed_by_user_id)
            self._require_quoted_products(opportunity.id)
            self._transition(
                opportunity,
                to_status=OpportunityStatus.GANADA,
                changed_by_user_id=changed_by_user_id,
            )
            self._session.flush()

        return opportunity

    def mark_as_lost(
        self,
        opportunity_id: int,
        loss_reason: LossReason | None,
        *,
        changed_by_user_id: int | None = None,
    ) -> Opportunity:
        with self._session.begin():
            opportunity = self._get_opportunity_for_update(opportunity_id)
            self._require_open(opportunity)
            if not isinstance(loss_reason, LossReason):
                raise InvalidLossReasonError(
                    "A valid loss reason is required to mark an opportunity lost"
                )
            self._validate_history_user(changed_by_user_id)
            self._transition(
                opportunity,
                to_status=OpportunityStatus.PERDIDA,
                changed_by_user_id=changed_by_user_id,
                loss_reason=loss_reason,
            )
            self._session.flush()

        return opportunity

    def update_quote_products(
        self,
        opportunity_id: int,
        products: list[QuoteProductInput],
    ) -> Opportunity:
        """Replaces the current quote without creating a quote revision.

        An inactive product may remain and have its quantity changed when it already
        belongs to the opportunity. It cannot be introduced as a new quote product.
        """
        with self._session.begin():
            opportunity = self._get_opportunity_for_update(opportunity_id)
            self._require_quote_editable(opportunity)
            existing_lines = self._get_quote_products(opportunity.id)
            validated_products = self._validate_quote_products(
                products,
                existing_product_ids=frozenset(existing_lines),
            )
            self._replace_quote_products(
                opportunity.id,
                validated_products,
                existing_lines=existing_lines,
            )
            self._session.flush()

        return opportunity

    def assign_user(
        self,
        opportunity_id: int,
        assigned_user_id: int | None,
    ) -> Opportunity:
        with self._session.begin():
            opportunity = self._get_opportunity_for_update(opportunity_id)
            self._validate_assigned_user(assigned_user_id)
            opportunity.assigned_user_id = assigned_user_id
            opportunity.updated_at = datetime.now(UTC)
            self._session.flush()

        return opportunity

    def soft_delete_opportunity(self, opportunity_id: int) -> Opportunity:
        """Soft-delete a duplicate/error and resolve its active notifications."""
        with self._session.begin():
            opportunity = self._get_any_opportunity_for_update(opportunity_id)
            deleted_at = datetime.now(UTC)
            if opportunity.deleted_at is None:
                opportunity.deleted_at = deleted_at
                opportunity.updated_at = deleted_at
            NotificationService(
                self._session
            ).resolve_stale_for_opportunity_in_transaction(
                opportunity.id,
                resolved_at=deleted_at,
            )
            self._session.flush()
        return opportunity

    def _get_available_customer(self, customer_id: int) -> Customer:
        customer = self._session.scalar(
            select(Customer).where(Customer.id == customer_id).with_for_update()
        )
        if customer is None:
            raise EntityNotFoundError("Customer", customer_id)
        if customer.deleted_at is not None:
            raise DeletedCustomerError(customer_id)
        return customer

    def _get_opportunity_for_update(self, opportunity_id: int) -> Opportunity:
        opportunity = self._session.scalar(
            select(Opportunity)
            .where(
                Opportunity.id == opportunity_id,
                Opportunity.deleted_at.is_(None),
            )
            .with_for_update()
        )
        if opportunity is None:
            raise EntityNotFoundError("Opportunity", opportunity_id)
        return opportunity

    def _get_any_opportunity_for_update(self, opportunity_id: int) -> Opportunity:
        opportunity = self._session.scalar(
            select(Opportunity)
            .where(Opportunity.id == opportunity_id)
            .with_for_update()
        )
        if opportunity is None:
            raise EntityNotFoundError("Opportunity", opportunity_id)
        return opportunity

    def _validate_assigned_user(self, user_id: int | None) -> None:
        if user_id is None:
            return
        user = self._get_user_for_update(user_id)
        if not user.is_active:
            raise InactiveUserError(user_id)

    def _validate_history_user(self, user_id: int | None) -> None:
        if user_id is not None and self._session.get(User, user_id) is None:
            raise EntityNotFoundError("User", user_id)

    def _get_user_for_update(self, user_id: int) -> User:
        user = self._session.scalar(
            select(User).where(User.id == user_id).with_for_update()
        )
        if user is None:
            raise EntityNotFoundError("User", user_id)
        return user

    def _validate_quote_products(
        self,
        products: list[QuoteProductInput],
        *,
        existing_product_ids: frozenset[int],
    ) -> dict[int, Decimal]:
        if not products:
            raise InvalidQuoteProductsError("A quote requires at least one product")

        quantities_by_product: dict[int, Decimal] = {}
        for item in products:
            if item.product_id in quantities_by_product:
                raise InvalidQuoteProductsError(
                    f"Product {item.product_id} is duplicated in the quote"
                )
            if (
                not isinstance(item.quantity_kg, Decimal)
                or not item.quantity_kg.is_finite()
                or item.quantity_kg <= 0
            ):
                raise InvalidQuoteProductsError(
                    f"Product {item.product_id} requires a positive quantity"
                )
            quantities_by_product[item.product_id] = item.quantity_kg

        product_ids = frozenset(quantities_by_product)
        persisted_products = self._session.scalars(
            select(Product)
            .where(Product.id.in_(product_ids))
            .order_by(Product.id)
            .with_for_update()
        ).all()
        products_by_id = {product.id: product for product in persisted_products}

        missing_product_ids = sorted(product_ids - products_by_id.keys())
        if missing_product_ids:
            raise EntityNotFoundError("Product", missing_product_ids[0])

        for product_id, product in products_by_id.items():
            if not product.is_active and product_id not in existing_product_ids:
                raise InactiveProductError(product_id)

        return quantities_by_product

    def _get_quote_products(
        self,
        opportunity_id: int,
    ) -> dict[int, OpportunityProduct]:
        lines = self._session.scalars(
            select(OpportunityProduct).where(
                OpportunityProduct.opportunity_id == opportunity_id
            )
        ).all()
        return {line.product_id: line for line in lines}

    def _replace_quote_products(
        self,
        opportunity_id: int,
        quantities_by_product: dict[int, Decimal],
        *,
        existing_lines: dict[int, OpportunityProduct] | None = None,
    ) -> None:
        current_lines = (
            existing_lines
            if existing_lines is not None
            else self._get_quote_products(opportunity_id)
        )

        for removed_product_id in current_lines.keys() - quantities_by_product.keys():
            self._session.delete(current_lines[removed_product_id])

        for product_id, quantity_kg in quantities_by_product.items():
            line = current_lines.get(product_id)
            if line is None:
                self._session.add(
                    OpportunityProduct(
                        opportunity_id=opportunity_id,
                        product_id=product_id,
                        quantity_kg=quantity_kg,
                    )
                )
            else:
                line.quantity_kg = quantity_kg
                line.updated_at = datetime.now(UTC)

    def _require_transition(
        self,
        opportunity: Opportunity,
        *,
        expected_status: OpportunityStatus,
        target_status: OpportunityStatus,
    ) -> None:
        self._require_open(opportunity)
        if opportunity.status is not expected_status:
            raise InvalidStateTransitionError(
                opportunity.id,
                opportunity.status,
                target_status,
            )

    def _require_open(self, opportunity: Opportunity) -> None:
        if opportunity.status in TERMINAL_STATUSES:
            raise ClosedOpportunityError(opportunity.id, opportunity.status)

    def _require_quote_editable(self, opportunity: Opportunity) -> None:
        self._require_open(opportunity)
        if opportunity.status not in {
            OpportunityStatus.COTIZADA,
            OpportunityStatus.NEGOCIACION,
        }:
            raise InvalidQuoteProductsError(
                "Quote products can only be edited in COTIZADA or NEGOCIACION"
            )

    def _require_quoted_products(self, opportunity_id: int) -> None:
        product_id = self._session.scalar(
            select(OpportunityProduct.product_id)
            .where(OpportunityProduct.opportunity_id == opportunity_id)
            .limit(1)
        )
        if product_id is None:
            raise InvalidQuoteProductsError(
                f"Opportunity {opportunity_id} requires at least one quoted product"
            )

    def _transition(
        self,
        opportunity: Opportunity,
        *,
        to_status: OpportunityStatus,
        changed_by_user_id: int | None,
        loss_reason: LossReason | None = None,
    ) -> None:
        from_status = opportunity.status
        changed_at = datetime.now(UTC)
        opportunity.status = to_status
        opportunity.loss_reason = loss_reason
        opportunity.current_status_entered_at = changed_at
        opportunity.updated_at = changed_at
        NotificationService(self._session).resolve_stale_for_opportunity_in_transaction(
            opportunity.id,
            resolved_at=changed_at,
        )
        self._add_history(
            opportunity=opportunity,
            from_status=from_status,
            to_status=to_status,
            changed_at=changed_at,
            changed_by_user_id=changed_by_user_id,
        )

    def _add_history(
        self,
        *,
        opportunity: Opportunity,
        from_status: OpportunityStatus | None,
        to_status: OpportunityStatus,
        changed_at: datetime,
        changed_by_user_id: int | None,
    ) -> None:
        self._session.add(
            OpportunityStatusHistory(
                opportunity_id=opportunity.id,
                from_status=from_status,
                to_status=to_status,
                changed_at=changed_at,
                changed_by_user_id=changed_by_user_id,
            )
        )
