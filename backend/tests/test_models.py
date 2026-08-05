from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, StatementError
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
    UserRole,
)


def create_customer(db_session: Session, name: str = "Cliente FAA") -> Customer:
    customer = Customer(name=name)
    db_session.add(customer)
    db_session.flush()
    return customer


def create_user(db_session: Session, email: str = "ventas@faa.test") -> User:
    user = User(
        full_name="Vendedor FAA",
        email=email,
        password_hash="hashed-password",
        role=UserRole.VENDEDOR,
    )
    db_session.add(user)
    db_session.flush()
    return user


def create_product(db_session: Session, name: str = "SuperPhalt") -> Product:
    product = Product(name=name)
    db_session.add(product)
    db_session.flush()
    return product


def create_opportunity(
    db_session: Session,
    customer: Customer,
    *,
    status: OpportunityStatus = OpportunityStatus.NUEVA,
    source: LeadSource = LeadSource.WEB,
    loss_reason: LossReason | None = None,
) -> Opportunity:
    opportunity = Opportunity(
        customer_id=customer.id,
        source=source,
        status=status,
        loss_reason=loss_reason,
    )
    db_session.add(opportunity)
    db_session.flush()
    return opportunity


def test_customer_creation_and_legendary_default(db_session: Session) -> None:
    customer = Customer(
        name="Constructora del Sur",
        company=None,
        email=None,
        phone=None,
        province="Buenos Aires",
    )
    db_session.add(customer)
    db_session.flush()

    assert customer.id is not None
    assert customer.legendary_historical_override is False
    assert customer.created_at.tzinfo is not None


@pytest.mark.parametrize("name", ["", "   "])
def test_customer_rejects_blank_name(db_session: Session, name: str) -> None:
    db_session.add(Customer(name=name))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_user_creation(db_session: Session) -> None:
    user = create_user(db_session)

    assert user.id is not None
    assert user.role is UserRole.VENDEDOR
    assert user.is_active is True


def test_user_email_is_case_insensitive_unique(db_session: Session) -> None:
    create_user(db_session, email="  Ventas@FAA.test ")
    db_session.add(
        User(
            full_name="Otro vendedor",
            email="ventas@faa.TEST",
            password_hash="another-hash",
            role=UserRole.VENDEDOR,
        )
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_user_rejects_unknown_role(db_session: Session) -> None:
    db_session.add(
        User(
            full_name="Usuario inválido",
            email="invalid-role@faa.test",
            password_hash="hashed-password",
            role="ADMIN",
        )
    )

    with pytest.raises(StatementError):
        db_session.flush()


def test_product_creation_and_deactivation(db_session: Session) -> None:
    product = create_product(db_session)
    product_id = product.id

    product.is_active = False
    db_session.flush()
    db_session.expire(product)

    persisted_product = db_session.get(Product, product_id)
    assert persisted_product is not None
    assert persisted_product.is_active is False


def test_product_name_is_case_insensitive_unique(db_session: Session) -> None:
    create_product(db_session, name="  SuperPhalt ")
    db_session.add(Product(name="superphalt"))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_opportunity_creation_allows_unassigned_user(db_session: Session) -> None:
    customer = create_customer(db_session)
    opportunity = Opportunity(customer_id=customer.id, source=LeadSource.WEB)
    db_session.add(opportunity)
    db_session.flush()

    assert opportunity.id is not None
    assert opportunity.assigned_user_id is None
    assert opportunity.status is OpportunityStatus.NUEVA
    assert opportunity.source is LeadSource.WEB
    assert opportunity.current_status_entered_at.tzinfo is not None


def test_opportunity_enforces_customer_foreign_key(db_session: Session) -> None:
    db_session.add(Opportunity(customer_id=999_999_999, source=LeadSource.WEB))

    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.parametrize("source", list(LeadSource))
def test_opportunity_accepts_valid_sources(
    db_session: Session,
    source: LeadSource,
) -> None:
    customer = create_customer(db_session, name=f"Cliente {source.value}")
    opportunity = create_opportunity(db_session, customer, source=source)

    assert opportunity.source is source


@pytest.mark.parametrize("status", list(OpportunityStatus))
def test_opportunity_accepts_valid_statuses(
    db_session: Session,
    status: OpportunityStatus,
) -> None:
    customer = create_customer(db_session, name=f"Cliente {status.value}")
    loss_reason = LossReason.PRECIO if status is OpportunityStatus.PERDIDA else None
    opportunity = create_opportunity(
        db_session,
        customer,
        status=status,
        loss_reason=loss_reason,
    )

    assert opportunity.status is status


def test_lost_opportunity_requires_loss_reason(db_session: Session) -> None:
    customer = create_customer(db_session)
    db_session.add(
        Opportunity(
            customer_id=customer.id,
            source=LeadSource.WEB,
            status=OpportunityStatus.PERDIDA,
        )
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.parametrize(
    "status",
    [
        OpportunityStatus.NUEVA,
        OpportunityStatus.COTIZADA,
        OpportunityStatus.NEGOCIACION,
        OpportunityStatus.GANADA,
    ],
)
def test_non_lost_opportunity_rejects_loss_reason(
    db_session: Session,
    status: OpportunityStatus,
) -> None:
    customer = create_customer(db_session, name=f"Cliente {status.value}")
    db_session.add(
        Opportunity(
            customer_id=customer.id,
            source=LeadSource.WEB,
            status=status,
            loss_reason=LossReason.OTRO,
        )
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.parametrize("quantity", [Decimal("0"), Decimal("-0.001")])
def test_opportunity_product_requires_positive_quantity(
    db_session: Session,
    quantity: Decimal,
) -> None:
    customer = create_customer(db_session)
    opportunity = create_opportunity(db_session, customer)
    product = create_product(db_session)
    db_session.add(
        OpportunityProduct(
            opportunity_id=opportunity.id,
            product_id=product.id,
            quantity_kg=quantity,
        )
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_opportunity_product_rejects_duplicate_product(db_session: Session) -> None:
    customer = create_customer(db_session)
    opportunity = create_opportunity(db_session, customer)
    product = create_product(db_session)
    first_line = OpportunityProduct(
        opportunity_id=opportunity.id,
        product_id=product.id,
        quantity_kg=Decimal("2500.000"),
    )
    db_session.add(first_line)
    db_session.flush()
    db_session.expunge(first_line)
    db_session.add(
        OpportunityProduct(
            opportunity_id=opportunity.id,
            product_id=product.id,
            quantity_kg=Decimal("1000.000"),
        )
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_status_history_allows_creation_transition(db_session: Session) -> None:
    customer = create_customer(db_session)
    opportunity = create_opportunity(db_session, customer)
    history = OpportunityStatusHistory(
        opportunity_id=opportunity.id,
        from_status=None,
        to_status=OpportunityStatus.NUEVA,
    )
    db_session.add(history)
    db_session.flush()

    assert history.id is not None
    assert history.from_status is None
    assert history.to_status is OpportunityStatus.NUEVA


def test_status_history_references_opportunity_and_user(db_session: Session) -> None:
    customer = create_customer(db_session)
    user = create_user(db_session)
    opportunity = create_opportunity(db_session, customer)
    history = OpportunityStatusHistory(
        opportunity=opportunity,
        from_status=OpportunityStatus.NUEVA,
        to_status=OpportunityStatus.COTIZADA,
        changed_by_user=user,
    )
    db_session.add(history)
    db_session.flush()

    assert history.opportunity_id == opportunity.id
    assert history.changed_by_user_id == user.id
    assert history in opportunity.status_history
    assert history in user.status_changes


def test_soft_delete_keeps_customer_and_opportunity_rows(db_session: Session) -> None:
    customer = create_customer(db_session)
    opportunity = create_opportunity(db_session, customer)
    customer_id = customer.id
    opportunity_id = opportunity.id
    deleted_at = datetime.now(UTC)

    customer.deleted_at = deleted_at
    opportunity.deleted_at = deleted_at
    db_session.flush()
    db_session.expire_all()

    persisted_customer = db_session.scalar(
        select(Customer).where(Customer.id == customer_id)
    )
    persisted_opportunity = db_session.scalar(
        select(Opportunity).where(Opportunity.id == opportunity_id)
    )

    assert persisted_customer is not None
    assert persisted_customer.deleted_at is not None
    assert persisted_opportunity is not None
    assert persisted_opportunity.deleted_at is not None
