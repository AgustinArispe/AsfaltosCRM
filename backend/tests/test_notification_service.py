from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_stale_opportunity_days
from app.db.session import SessionLocal
from app.models import (
    Customer,
    LeadSource,
    LossReason,
    Notification,
    Opportunity,
    OpportunityProduct,
    OpportunityStatus,
    OpportunityStatusHistory,
    Product,
    User,
    UserRole,
)
from app.services import NotificationService, OpportunityService, QuoteProductInput

NOW = datetime.now(UTC) - timedelta(seconds=1)


def persist(db_session: Session, *entities: object) -> None:
    db_session.add_all(entities)
    db_session.commit()


def make_opportunity(
    db_session: Session,
    *,
    status: OpportunityStatus,
    age_days: int,
    deleted: bool = False,
) -> Opportunity:
    customer = Customer(name=f"Cliente notification {uuid4().hex}")
    entered_at = NOW - timedelta(days=age_days)
    opportunity = Opportunity(
        customer=customer,
        source=LeadSource.WEB,
        status=status,
        loss_reason=(LossReason.OTRO if status is OpportunityStatus.PERDIDA else None),
        current_status_entered_at=entered_at,
        created_at=entered_at - timedelta(days=1),
        updated_at=entered_at,
        deleted_at=NOW if deleted else None,
    )
    persist(db_session, opportunity)
    return opportunity


def generate(db_session: Session, *, now: datetime = NOW) -> int:
    return NotificationService(db_session).generate_stale_opportunity_notifications(
        now=now,
        threshold_days=14,
    )


def notifications_for(
    db_session: Session,
    opportunity_id: int,
) -> list[Notification]:
    return list(
        db_session.scalars(
            select(Notification)
            .where(Notification.opportunity_id == opportunity_id)
            .order_by(Notification.created_at, Notification.id)
        )
    )


@pytest.mark.parametrize(
    ("status", "age_days", "deleted", "expected_count"),
    [
        (OpportunityStatus.NUEVA, 13, False, 0),
        (OpportunityStatus.NUEVA, 14, False, 1),
        (OpportunityStatus.COTIZADA, 15, False, 1),
        (OpportunityStatus.NEGOCIACION, 20, False, 1),
        (OpportunityStatus.GANADA, 20, False, 0),
        (OpportunityStatus.PERDIDA, 20, False, 0),
        (OpportunityStatus.NUEVA, 20, True, 0),
    ],
)
def test_generation_eligibility_rules(
    db_session: Session,
    status: OpportunityStatus,
    age_days: int,
    deleted: bool,
    expected_count: int,
) -> None:
    opportunity = make_opportunity(
        db_session,
        status=status,
        age_days=age_days,
        deleted=deleted,
    )

    created_count = generate(db_session)

    assert created_count == expected_count
    assert len(notifications_for(db_session, opportunity.id)) == expected_count


def test_generator_is_idempotent(db_session: Session) -> None:
    opportunity = make_opportunity(
        db_session,
        status=OpportunityStatus.NUEVA,
        age_days=14,
    )

    assert generate(db_session) == 1
    assert generate(db_session) == 0
    assert len(notifications_for(db_session, opportunity.id)) == 1


def test_concurrent_generation_creates_one_active_notification() -> None:
    entered_at = datetime.now(UTC) - timedelta(days=20_000)
    with SessionLocal.begin() as setup_session:
        customer = Customer(name=f"Concurrent notification {uuid4().hex}")
        opportunity = Opportunity(
            customer=customer,
            source=LeadSource.WEB,
            status=OpportunityStatus.NUEVA,
            current_status_entered_at=entered_at,
            created_at=entered_at - timedelta(days=1),
            updated_at=entered_at,
        )
        setup_session.add(opportunity)
        setup_session.flush()
        opportunity_id = opportunity.id
        customer_id = customer.id

    barrier = Barrier(2)

    def run_generator() -> int:
        barrier.wait()
        with SessionLocal() as session:
            return NotificationService(
                session
            ).generate_stale_opportunity_notifications(
                now=datetime.now(UTC),
                threshold_days=10_000,
            )

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(run_generator) for _ in range(2)]
            results = [future.result() for future in futures]
        with SessionLocal() as verification_session:
            notification_count = len(
                notifications_for(verification_session, opportunity_id)
            )
        assert sorted(results) == [0, 1]
        assert notification_count == 1
    finally:
        _cleanup_persisted_notification_data(opportunity_id, customer_id)


def test_transition_resolves_stale_and_new_stage_can_generate_again(
    db_session: Session,
) -> None:
    opportunity = make_opportunity(
        db_session,
        status=OpportunityStatus.NUEVA,
        age_days=15,
    )
    product = Product(name=f"Producto notification {uuid4().hex}")
    persist(db_session, product)
    assert generate(db_session) == 1

    OpportunityService(db_session).quote_opportunity(
        opportunity.id,
        [QuoteProductInput(product_id=product.id, quantity_kg=Decimal("1000"))],
    )
    first_notification = notifications_for(db_session, opportunity.id)[0]

    assert first_notification.resolved_at is not None
    assert first_notification.read_at is None

    opportunity.current_status_entered_at = NOW - timedelta(days=14)
    opportunity.updated_at = NOW
    db_session.commit()

    assert generate(db_session) == 1
    notifications = notifications_for(db_session, opportunity.id)
    assert len(notifications) == 2
    assert notifications[1].resolved_at is None


def test_win_resolves_active_stale_notification(db_session: Session) -> None:
    opportunity = _make_quoted_opportunity(
        db_session,
        status=OpportunityStatus.NEGOCIACION,
    )
    assert generate(db_session) == 1

    OpportunityService(db_session).mark_as_won(opportunity.id)

    assert notifications_for(db_session, opportunity.id)[0].resolved_at is not None


def test_lose_resolves_active_stale_notification(db_session: Session) -> None:
    opportunity = make_opportunity(
        db_session,
        status=OpportunityStatus.NUEVA,
        age_days=15,
    )
    assert generate(db_session) == 1

    OpportunityService(db_session).mark_as_lost(opportunity.id, LossReason.PRECIO)

    assert notifications_for(db_session, opportunity.id)[0].resolved_at is not None


def test_quote_product_edit_does_not_resolve_notification(
    db_session: Session,
) -> None:
    opportunity = _make_quoted_opportunity(
        db_session,
        status=OpportunityStatus.COTIZADA,
    )
    line = db_session.scalar(
        select(OpportunityProduct).where(
            OpportunityProduct.opportunity_id == opportunity.id
        )
    )
    assert line is not None
    opportunity_id = opportunity.id
    product_id = line.product_id
    db_session.rollback()
    assert generate(db_session) == 1

    OpportunityService(db_session).update_quote_products(
        opportunity_id,
        [
            QuoteProductInput(
                product_id=product_id,
                quantity_kg=Decimal("2000"),
            )
        ],
    )

    assert notifications_for(db_session, opportunity_id)[0].resolved_at is None


def test_assignment_does_not_resolve_notification(db_session: Session) -> None:
    opportunity = make_opportunity(
        db_session,
        status=OpportunityStatus.NUEVA,
        age_days=15,
    )
    user = User(
        full_name="Vendedor notification",
        email=f"notification-{uuid4().hex}@faa.test",
        password_hash="hashed-password",
        role=UserRole.VENDEDOR,
    )
    persist(db_session, user)
    assert generate(db_session) == 1

    OpportunityService(db_session).assign_user(opportunity.id, user.id)

    assert notifications_for(db_session, opportunity.id)[0].resolved_at is None


def test_soft_delete_resolves_active_notification(db_session: Session) -> None:
    opportunity = make_opportunity(
        db_session,
        status=OpportunityStatus.NUEVA,
        age_days=15,
    )
    assert generate(db_session) == 1

    OpportunityService(db_session).soft_delete_opportunity(opportunity.id)

    notification = notifications_for(db_session, opportunity.id)[0]
    assert opportunity.deleted_at is not None
    assert notification.resolved_at is not None


def test_mark_read_is_global_idempotent_and_does_not_resolve(
    db_session: Session,
) -> None:
    opportunity = make_opportunity(
        db_session,
        status=OpportunityStatus.NUEVA,
        age_days=15,
    )
    assert generate(db_session) == 1
    notification = notifications_for(db_session, opportunity.id)[0]
    notification_id = notification.id
    db_session.rollback()
    service = NotificationService(db_session)
    first_read_at = NOW + timedelta(minutes=1)

    first_read = service.mark_as_read(notification_id, now=first_read_at)
    second_read = service.mark_as_read(
        notification_id,
        now=NOW + timedelta(minutes=2),
    )

    assert first_read.read_at == first_read_at
    assert second_read.read_at == first_read_at
    assert second_read.resolved_at is None


def test_mark_all_reads_only_active_unread_notifications(db_session: Session) -> None:
    active_opportunity = make_opportunity(
        db_session,
        status=OpportunityStatus.NUEVA,
        age_days=15,
    )
    resolved_opportunity = make_opportunity(
        db_session,
        status=OpportunityStatus.NUEVA,
        age_days=16,
    )
    assert generate(db_session) == 2
    OpportunityService(db_session).mark_as_lost(
        resolved_opportunity.id,
        LossReason.OTRO,
    )

    updated_count = NotificationService(db_session).mark_all_active_as_read(
        now=NOW + timedelta(minutes=1)
    )

    active = notifications_for(db_session, active_opportunity.id)[0]
    resolved = notifications_for(db_session, resolved_opportunity.id)[0]
    assert updated_count == 1
    assert active.read_at is not None
    assert resolved.resolved_at is not None
    assert resolved.read_at is None


def test_notification_service_rejects_naive_time_and_invalid_threshold(
    db_session: Session,
) -> None:
    service = NotificationService(db_session)
    with pytest.raises(ValueError, match="timezone-aware"):
        service.generate_stale_opportunity_notifications(
            now=datetime(2026, 8, 5),
            threshold_days=14,
        )
    with pytest.raises(ValueError, match="greater than zero"):
        service.generate_stale_opportunity_notifications(
            now=NOW,
            threshold_days=0,
        )


@pytest.mark.parametrize("raw_value", ["0", "-1", "not-an-integer"])
def test_stale_days_configuration_rejects_invalid_values(
    monkeypatch: pytest.MonkeyPatch,
    raw_value: str,
) -> None:
    get_stale_opportunity_days.cache_clear()
    monkeypatch.setenv("STALE_OPPORTUNITY_DAYS", raw_value)
    try:
        with pytest.raises(RuntimeError):
            get_stale_opportunity_days()
    finally:
        get_stale_opportunity_days.cache_clear()


def _make_quoted_opportunity(
    db_session: Session,
    *,
    status: OpportunityStatus,
) -> Opportunity:
    opportunity = make_opportunity(
        db_session,
        status=status,
        age_days=15,
    )
    product = Product(name=f"Producto cotizado {uuid4().hex}")
    persist(db_session, product)
    persist(
        db_session,
        OpportunityProduct(
            opportunity_id=opportunity.id,
            product_id=product.id,
            quantity_kg=Decimal("1000"),
        ),
    )
    return opportunity


def _cleanup_persisted_notification_data(
    opportunity_id: int,
    customer_id: int,
) -> None:
    with SessionLocal.begin() as session:
        session.execute(
            delete(Notification).where(Notification.opportunity_id == opportunity_id)
        )
        session.execute(
            delete(OpportunityStatusHistory).where(
                OpportunityStatusHistory.opportunity_id == opportunity_id
            )
        )
        session.execute(
            delete(OpportunityProduct).where(
                OpportunityProduct.opportunity_id == opportunity_id
            )
        )
        session.execute(delete(Opportunity).where(Opportunity.id == opportunity_id))
        session.execute(delete(Customer).where(Customer.id == customer_id))
