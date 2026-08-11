from dataclasses import dataclass
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Customer,
    CustomerLegendaryEvent,
    LegendaryEventType,
    Opportunity,
    OpportunityStatus,
)
from app.services.customer_identity_service import acquire_advisory_locks
from app.services.errors import EntityNotFoundError

BUENOS_AIRES = ZoneInfo("America/Argentina/Buenos_Aires")


@dataclass(frozen=True, slots=True)
class LegendaryBatchResult:
    evaluated: int
    changed: int
    last_customer_id: int | None
    has_more: bool


class LegendaryService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def recompute_customer(
        self,
        customer_id: int,
        *,
        evaluated_at: datetime | None = None,
    ) -> Customer:
        with self._session.begin():
            customer, _ = self.recompute_customer_in_transaction(
                customer_id,
                evaluated_at=evaluated_at or datetime.now(UTC),
            )
            return customer

    def recompute_customer_in_transaction(
        self,
        customer_id: int,
        *,
        evaluated_at: datetime,
    ) -> tuple[Customer, bool]:
        _require_aware(evaluated_at)
        acquire_advisory_locks(
            self._session, (("legendary-customer", str(customer_id)),)
        )
        customer = self._session.scalar(
            select(Customer).where(Customer.id == customer_id).with_for_update()
        )
        if customer is None:
            raise EntityNotFoundError("Customer", customer_id)
        first_won = self._session.scalar(
            select(Opportunity)
            .where(
                Opportunity.customer_id == customer_id,
                Opportunity.status == OpportunityStatus.GANADA,
                Opportunity.deleted_at.is_(None),
            )
            .order_by(Opportunity.created_at, Opportunity.id)
            .limit(1)
        )
        automatic = first_won is not None and evaluated_at.astimezone(
            BUENOS_AIRES
        ) >= _third_anniversary(first_won.created_at)
        before_automatic = customer.legendary_automatic
        before_effective = customer.is_legendary
        customer.legendary_automatic = automatic
        customer.legendary_automatic_evaluated_at = evaluated_at.astimezone(UTC)
        changed = before_automatic != automatic
        if changed:
            self._session.add(
                CustomerLegendaryEvent(
                    customer_id=customer.id,
                    event_type=LegendaryEventType.AUTOMATIC_CHANGED,
                    before_manual=customer.legendary_historical_override,
                    after_manual=customer.legendary_historical_override,
                    before_automatic=before_automatic,
                    after_automatic=automatic,
                    before_effective=before_effective,
                    after_effective=customer.is_legendary,
                    first_won_opportunity_id=(first_won.id if first_won else None),
                    first_won_created_at=(first_won.created_at if first_won else None),
                    actor_user_id=None,
                    occurred_at=evaluated_at,
                )
            )
        self._session.flush()
        return customer, changed

    def recompute_batch(
        self,
        *,
        after_customer_id: int,
        batch_size: int,
        evaluated_at: datetime,
    ) -> LegendaryBatchResult:
        if batch_size <= 0 or batch_size > 1000:
            raise ValueError("batch_size must be between 1 and 1000")
        _require_aware(evaluated_at)
        with self._session.begin():
            customer_ids = list(
                self._session.scalars(
                    select(Customer.id)
                    .where(Customer.id > after_customer_id)
                    .order_by(Customer.id)
                    .limit(batch_size + 1)
                )
            )
            selected_ids = customer_ids[:batch_size]
            changed = 0
            for customer_id in selected_ids:
                _, was_changed = self.recompute_customer_in_transaction(
                    customer_id,
                    evaluated_at=evaluated_at,
                )
                changed += int(was_changed)
        return LegendaryBatchResult(
            evaluated=len(selected_ids),
            changed=changed,
            last_customer_id=(selected_ids[-1] if selected_ids else None),
            has_more=len(customer_ids) > batch_size,
        )

    def record_manual_change_in_transaction(
        self,
        customer: Customer,
        *,
        new_value: bool,
        actor_user_id: int,
        occurred_at: datetime,
    ) -> None:
        acquire_advisory_locks(
            self._session, (("legendary-customer", str(customer.id)),)
        )
        before_manual = customer.legendary_historical_override
        if before_manual == new_value:
            return
        before_effective = customer.is_legendary
        customer.legendary_historical_override = new_value
        self._session.add(
            CustomerLegendaryEvent(
                customer_id=customer.id,
                event_type=LegendaryEventType.MANUAL_OVERRIDE_CHANGED,
                before_manual=before_manual,
                after_manual=new_value,
                before_automatic=customer.legendary_automatic,
                after_automatic=customer.legendary_automatic,
                before_effective=before_effective,
                after_effective=customer.is_legendary,
                first_won_opportunity_id=None,
                first_won_created_at=None,
                actor_user_id=actor_user_id,
                occurred_at=occurred_at,
            )
        )


def _third_anniversary(created_at: datetime) -> datetime:
    _require_aware(created_at)
    local = created_at.astimezone(BUENOS_AIRES)
    try:
        return local.replace(year=local.year + 3)
    except ValueError:
        return local.replace(year=local.year + 3, day=28)


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
