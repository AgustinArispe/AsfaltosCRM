from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import (
    Customer,
    LeadSource,
    ManualOpportunityCreationCommand,
    Notification,
    Opportunity,
    OpportunityStatus,
    OpportunityStatusHistory,
    OpportunityTransitionKind,
    User,
    UserRole,
)
from app.services.errors import (
    EntityNotFoundError,
    ManualCustomerIdentityAmbiguousError,
    ManualCustomerIdentityDeletedError,
    ManualCustomerMatchExistsError,
    ManualOpportunityCommandConflictError,
    PermissionDeniedError,
)
from app.services.manual_opportunity_service import (
    ExistingCustomerInput,
    ManualOpportunityService,
    NewCustomerInput,
)


def make_user(
    *,
    email: str,
    role: UserRole = UserRole.SUPERVISOR,
    is_active: bool = True,
) -> User:
    return User(
        full_name=email.split("@", maxsplit=1)[0],
        email=email,
        password_hash=hash_password("manual-opportunity-test-password"),
        role=role,
        is_active=is_active,
    )


def make_customer(
    *,
    name: str,
    email: str | None = None,
    phone: str | None = None,
    deleted_at: datetime | None = None,
) -> Customer:
    return Customer(
        name=name,
        email=email,
        phone=phone,
        deleted_at=deleted_at,
        legendary_historical_override=False,
    )


def test_existing_customer_creation_is_referido_new_and_audited(
    db_session: Session,
) -> None:
    actor = make_user(email="actor-manual@faa.test")
    assignee = make_user(email="responsable-manual@faa.test")
    customer = make_customer(name="Cliente existente")
    db_session.add_all([actor, assignee, customer])
    db_session.commit()

    result = ManualOpportunityService(db_session).create(
        command_id=uuid4(),
        customer_input=ExistingCustomerInput(customer_id=customer.id),
        assigned_user_id=assignee.id,
        actor=actor,
    )

    opportunity = db_session.get(Opportunity, result.opportunity_id)
    history = db_session.scalar(
        select(OpportunityStatusHistory).where(
            OpportunityStatusHistory.opportunity_id == result.opportunity_id
        )
    )
    assert result.created is True
    assert opportunity is not None
    assert opportunity.source is LeadSource.REFERIDO
    assert opportunity.status is OpportunityStatus.NUEVA
    assert opportunity.assigned_user_id == assignee.id
    assert history is not None
    assert history.from_status is None
    assert history.to_status is OpportunityStatus.NUEVA
    assert history.transition_kind is OpportunityTransitionKind.CREATED
    assert history.changed_by_user_id == actor.id


def test_new_customer_and_opportunity_are_atomic(db_session: Session) -> None:
    actor = make_user(email="atomic-manual@faa.test")
    db_session.add(actor)
    db_session.commit()

    with pytest.raises(EntityNotFoundError):
        ManualOpportunityService(db_session).create(
            command_id=uuid4(),
            customer_input=NewCustomerInput(
                name="Cliente que debe revertirse",
                company=None,
                phone=None,
                email=None,
                province="Mendoza",
            ),
            assigned_user_id=999_999_999,
            actor=actor,
        )

    assert (
        db_session.scalar(
            select(func.count())
            .select_from(Customer)
            .where(Customer.name == "Cliente que debe revertirse")
        )
        == 0
    )
    assert (
        db_session.scalar(
            select(func.count()).select_from(ManualOpportunityCreationCommand)
        )
        == 0
    )


def test_manual_command_replay_is_idempotent_without_duplicate_notification(
    db_session: Session,
) -> None:
    actor = make_user(email="retry-manual@faa.test")
    customer = make_customer(name="Cliente replay")
    db_session.add_all([actor, customer])
    db_session.commit()
    command_id = uuid4()
    service = ManualOpportunityService(db_session)

    first = service.create(
        command_id=command_id,
        customer_input=ExistingCustomerInput(customer_id=customer.id),
        assigned_user_id=None,
        actor=actor,
    )
    replay = service.create(
        command_id=command_id,
        customer_input=ExistingCustomerInput(customer_id=customer.id),
        assigned_user_id=None,
        actor=actor,
    )

    assert first.created is True
    assert replay == type(replay)(opportunity_id=first.opportunity_id, created=False)
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(Opportunity)
            .where(Opportunity.id == first.opportunity_id)
        )
        == 1
    )
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.opportunity_id == first.opportunity_id)
        )
        == 1
    )


def test_manual_command_rejects_changed_or_cross_actor_replay(
    db_session: Session,
) -> None:
    first_actor = make_user(email="first-actor@faa.test")
    second_actor = make_user(email="second-actor@faa.test")
    customer = make_customer(name="Cliente comando")
    db_session.add_all([first_actor, second_actor, customer])
    db_session.commit()
    command_id = uuid4()
    service = ManualOpportunityService(db_session)
    service.create(
        command_id=command_id,
        customer_input=ExistingCustomerInput(customer_id=customer.id),
        assigned_user_id=None,
        actor=first_actor,
    )

    with pytest.raises(ManualOpportunityCommandConflictError):
        service.create(
            command_id=command_id,
            customer_input=ExistingCustomerInput(customer_id=customer.id),
            assigned_user_id=None,
            actor=second_actor,
        )
    with pytest.raises(ManualOpportunityCommandConflictError):
        service.create(
            command_id=command_id,
            customer_input=NewCustomerInput(
                name="Otro cliente",
                company=None,
                phone=None,
                email=None,
                province=None,
            ),
            assigned_user_id=None,
            actor=first_actor,
        )


def test_new_customer_exact_active_match_is_not_silently_reused(
    db_session: Session,
) -> None:
    actor = make_user(email="match-actor@faa.test")
    customer = make_customer(name="Cliente coincidente", email="cliente@faa.test")
    db_session.add_all([actor, customer])
    db_session.commit()

    with pytest.raises(ManualCustomerMatchExistsError) as captured:
        ManualOpportunityService(db_session).create(
            command_id=uuid4(),
            customer_input=NewCustomerInput(
                name="Nombre ingresado",
                company=None,
                phone=None,
                email=" CLIENTE@FAA.TEST ",
                province=None,
            ),
            assigned_user_id=None,
            actor=actor,
        )

    assert captured.value.customer.id == customer.id


def test_new_customer_ambiguous_and_deleted_matches_are_rejected(
    db_session: Session,
) -> None:
    actor = make_user(email="conflict-actor@faa.test")
    first = make_customer(name="Email", email="ambigua@faa.test")
    second = make_customer(name="Teléfono", phone="+54 9 11 5555-0101")
    deleted = make_customer(
        name="Eliminado",
        email="eliminado@faa.test",
        deleted_at=datetime.now(UTC) + timedelta(seconds=1),
    )
    db_session.add_all([actor, first, second, deleted])
    db_session.commit()
    service = ManualOpportunityService(db_session)

    with pytest.raises(ManualCustomerIdentityAmbiguousError):
        service.create(
            command_id=uuid4(),
            customer_input=NewCustomerInput(
                name="Ambiguo",
                company=None,
                phone="+5491155550101",
                email="ambigua@faa.test",
                province=None,
            ),
            assigned_user_id=None,
            actor=actor,
        )
    with pytest.raises(ManualCustomerIdentityDeletedError):
        service.create(
            command_id=uuid4(),
            customer_input=NewCustomerInput(
                name="Eliminado nuevo",
                company=None,
                phone=None,
                email="eliminado@faa.test",
                province=None,
            ),
            assigned_user_id=None,
            actor=actor,
        )


def test_vendor_cannot_assign_manual_opportunity(db_session: Session) -> None:
    vendor = make_user(email="vendor-manual@faa.test", role=UserRole.VENDEDOR)
    assignee = make_user(email="assignee-manual@faa.test")
    customer = make_customer(name="Cliente vendedor")
    db_session.add_all([vendor, assignee, customer])
    db_session.commit()

    with pytest.raises(PermissionDeniedError):
        ManualOpportunityService(db_session).create(
            command_id=uuid4(),
            customer_input=ExistingCustomerInput(customer_id=customer.id),
            assigned_user_id=assignee.id,
            actor=vendor,
        )
