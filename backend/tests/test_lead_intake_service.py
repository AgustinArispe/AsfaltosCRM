from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import delete, event, func, select, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapper, Session

from app.db.session import SessionLocal
from app.models import (
    Customer,
    LeadIntake,
    LeadSource,
    Opportunity,
    OpportunityStatus,
    OpportunityStatusHistory,
)
from app.services import (
    CustomerIdentityConflictError,
    LeadIntakeIdempotencyConflictError,
    LeadIntakeInput,
    LeadIntakeResult,
    LeadIntakeService,
)
from app.services.lead_intake_service import comparable_phone, normalize_email


def make_intake(
    *,
    external_submission_id: str | None = None,
    name: str = "  Juan Pérez  ",
    company: str | None = "  Constructora Sur  ",
    email: str | None = "  JUAN@EJEMPLO.COM  ",
    phone: str | None = "+54 (9) 249-123-4567",
    province: str | None = "  Buenos Aires  ",
    message: str | None = "  Primera línea\r\nSegunda línea  ",
) -> LeadIntakeInput:
    return LeadIntakeInput(
        name=name,
        company=company,
        email=email,
        phone=phone,
        province=province,
        message=message,
        source=LeadSource.WEB,
        external_submission_id=external_submission_id or uuid4().hex,
    )


def persist(db_session: Session, *entities: object) -> None:
    db_session.add_all(entities)
    db_session.commit()


def histories(
    db_session: Session,
    opportunity_id: int,
) -> list[OpportunityStatusHistory]:
    return list(
        db_session.scalars(
            select(OpportunityStatusHistory).where(
                OpportunityStatusHistory.opportunity_id == opportunity_id
            )
        )
    )


def test_new_customer_opportunity_intake_and_history_are_created_atomically(
    db_session: Session,
) -> None:
    result = LeadIntakeService(db_session).intake(make_intake())

    customer = db_session.get(Customer, result.customer_id)
    opportunity = db_session.get(Opportunity, result.opportunity_id)
    intake = db_session.get(LeadIntake, result.intake_id)
    history = histories(db_session, result.opportunity_id)

    assert result.created is True
    assert customer is not None
    assert customer.name == "Juan Pérez"
    assert customer.email == "juan@ejemplo.com"
    assert customer.phone == "+54 (9) 249-123-4567"
    assert opportunity is not None
    assert opportunity.source is LeadSource.WEB
    assert opportunity.status is OpportunityStatus.NUEVA
    assert opportunity.assigned_user_id is None
    assert intake is not None
    assert intake.opportunity_id == opportunity.id
    assert len(history) == 1
    assert history[0].from_status is None
    assert history[0].to_status is OpportunityStatus.NUEVA
    assert history[0].changed_by_user_id is None


def test_matches_existing_customer_by_normalized_email(db_session: Session) -> None:
    customer = Customer(name="Cliente Email", email=" Juan@Ejemplo.com ")
    persist(db_session, customer)

    result = LeadIntakeService(db_session).intake(
        make_intake(email="juan@ejemplo.com", phone=None)
    )

    assert result.customer_id == customer.id


def test_matches_existing_customer_by_comparable_phone(db_session: Session) -> None:
    customer = Customer(name="Cliente Phone", phone="+54 9 249 123-4567")
    persist(db_session, customer)

    result = LeadIntakeService(db_session).intake(
        make_intake(email=None, phone="+54 (9) 249-123-4567")
    )

    assert result.customer_id == customer.id


def test_email_match_has_priority_when_phone_has_no_match(db_session: Session) -> None:
    customer = Customer(name="Cliente Email", email="prioridad@ejemplo.com")
    persist(db_session, customer)

    result = LeadIntakeService(db_session).intake(
        make_intake(email="PRIORIDAD@EJEMPLO.COM", phone="11 9999-8888")
    )

    assert result.customer_id == customer.id


def test_conflicting_email_and_phone_customers_fail_completely(
    db_session: Session,
) -> None:
    email_customer = Customer(name="Cliente A", email="conflicto@ejemplo.com")
    phone_customer = Customer(name="Cliente B", phone="+54 11 4444-5555")
    persist(db_session, email_customer, phone_customer)
    counts_before = _entity_counts(db_session)
    db_session.rollback()

    with pytest.raises(CustomerIdentityConflictError):
        LeadIntakeService(db_session).intake(
            make_intake(
                email="conflicto@ejemplo.com",
                phone="+54 (11) 4444-5555",
            )
        )

    assert _entity_counts(db_session) == counts_before


@pytest.mark.parametrize("matching_field", ["email", "phone"])
def test_multiple_customer_matches_are_rejected(
    db_session: Session,
    matching_field: str,
) -> None:
    if matching_field == "email":
        customers = [
            Customer(name="Email A", email="shared@ejemplo.com"),
            Customer(name="Email B", email=" SHARED@EJEMPLO.COM "),
        ]
        intake = make_intake(email="shared@ejemplo.com", phone=None)
    else:
        customers = [
            Customer(name="Phone A", phone="+54 11 4444-5555"),
            Customer(name="Phone B", phone="+54 (11) 4444 5555"),
        ]
        intake = make_intake(email=None, phone="+54-11-4444-5555")
    persist(db_session, *customers)

    with pytest.raises(CustomerIdentityConflictError):
        LeadIntakeService(db_session).intake(intake)


def test_deleted_customer_is_not_reused(db_session: Session) -> None:
    deleted_customer = Customer(
        name="Cliente eliminado",
        email="deleted@ejemplo.com",
    )
    persist(db_session, deleted_customer)
    deleted_customer.deleted_at = datetime.now(UTC)
    db_session.commit()

    result = LeadIntakeService(db_session).intake(
        make_intake(email="deleted@ejemplo.com", phone=None)
    )

    assert result.customer_id != deleted_customer.id
    persisted_deleted_customer = db_session.get(Customer, deleted_customer.id)
    assert persisted_deleted_customer is not None
    assert persisted_deleted_customer.deleted_at is not None


def test_enrichment_only_fills_missing_fields_and_updates_timestamp(
    db_session: Session,
) -> None:
    customer = Customer(
        name="Nombre original",
        company="Empresa original",
        email="enrich@ejemplo.com",
        phone=None,
        province=None,
    )
    persist(db_session, customer)
    original_updated_at = customer.updated_at

    result = LeadIntakeService(db_session).intake(
        make_intake(
            name="Nombre nuevo",
            company="Empresa nueva",
            email="enrich@ejemplo.com",
            phone="11 4444-5555",
            province="Córdoba",
        )
    )

    assert result.customer_id == customer.id
    assert customer.name == "Nombre original"
    assert customer.company == "Empresa original"
    assert customer.email == "enrich@ejemplo.com"
    assert customer.phone == "11 4444-5555"
    assert customer.province == "Córdoba"
    assert customer.updated_at >= original_updated_at


def test_phone_match_does_not_replace_existing_different_email(
    db_session: Session,
) -> None:
    customer = Customer(
        name="Cliente existente",
        email="actual@ejemplo.com",
        phone="11 5555-1234",
    )
    persist(db_session, customer)

    result = LeadIntakeService(db_session).intake(
        make_intake(email="nuevo@ejemplo.com", phone="(11) 5555 1234")
    )
    intake = db_session.get(LeadIntake, result.intake_id)

    assert result.customer_id == customer.id
    assert customer.email == "actual@ejemplo.com"
    assert intake is not None
    assert intake.submitted_email == "nuevo@ejemplo.com"


def test_submission_with_short_phone_does_not_match_automatically(
    db_session: Session,
) -> None:
    customer = Customer(name="Teléfono corto", phone="123-45")
    persist(db_session, customer)

    result = LeadIntakeService(db_session).intake(
        make_intake(email=None, phone="123 45")
    )

    assert result.customer_id != customer.id


def test_customer_without_real_enrichment_keeps_updated_at(
    db_session: Session,
) -> None:
    customer = Customer(
        name="Nombre original",
        company="Empresa original",
        email="unchanged@ejemplo.com",
        phone="11 4444-5555",
        province="Buenos Aires",
    )
    persist(db_session, customer)
    original_updated_at = customer.updated_at

    LeadIntakeService(db_session).intake(
        make_intake(
            name="Nombre distinto",
            company="Empresa distinta",
            email="unchanged@ejemplo.com",
            phone="11 4444-5555",
            province="Córdoba",
        )
    )

    assert customer.updated_at == original_updated_at


def test_snapshot_and_message_are_normalized_without_raw_payload(
    db_session: Session,
) -> None:
    result = LeadIntakeService(db_session).intake(make_intake())
    intake = db_session.get(LeadIntake, result.intake_id)

    assert intake is not None
    assert intake.submitted_name == "Juan Pérez"
    assert intake.submitted_company == "Constructora Sur"
    assert intake.submitted_email == "juan@ejemplo.com"
    assert intake.submitted_phone == "+54 (9) 249-123-4567"
    assert intake.submitted_province == "Buenos Aires"
    assert intake.message == "Primera línea\nSegunda línea"


def test_distinct_external_ids_always_create_distinct_opportunities(
    db_session: Session,
) -> None:
    service = LeadIntakeService(db_session)
    first = service.intake(make_intake(external_submission_id="submission-1"))
    second = service.intake(make_intake(external_submission_id="submission-2"))

    assert first.customer_id == second.customer_id
    assert first.opportunity_id != second.opportunity_id
    assert first.intake_id != second.intake_id


def test_identical_replay_returns_original_result(db_session: Session) -> None:
    service = LeadIntakeService(db_session)
    intake = make_intake(external_submission_id="replay-identical")
    counts_before = _entity_counts(db_session)
    db_session.rollback()

    first = service.intake(intake)
    replay = service.intake(intake)

    assert first.created is True
    assert replay == LeadIntakeResult(
        intake_id=first.intake_id,
        customer_id=first.customer_id,
        opportunity_id=first.opportunity_id,
        created=False,
    )
    assert _entity_counts(db_session) == tuple(count + 1 for count in counts_before)


def test_replay_compares_the_normalized_snapshot(db_session: Session) -> None:
    service = LeadIntakeService(db_session)
    external_id = "normalized-replay"
    first = service.intake(make_intake(external_submission_id=external_id))

    replay = service.intake(
        make_intake(
            external_submission_id=f"  {external_id}  ",
            name="Juan Pérez",
            company="Constructora Sur",
            email="juan@ejemplo.com",
            phone="+54 (9) 249-123-4567",
            province="Buenos Aires",
            message="Primera línea\nSegunda línea",
        )
    )

    assert replay.created is False
    assert replay.intake_id == first.intake_id


def test_same_external_id_with_different_normalized_payload_conflicts(
    db_session: Session,
) -> None:
    service = LeadIntakeService(db_session)
    service.intake(make_intake(external_submission_id="replay-conflict"))
    counts_after_first = _entity_counts(db_session)
    db_session.rollback()

    with pytest.raises(LeadIntakeIdempotencyConflictError):
        service.intake(
            make_intake(
                external_submission_id="replay-conflict",
                message="Otro mensaje",
            )
        )

    assert _entity_counts(db_session) == counts_after_first


def test_failure_rolls_back_customer_opportunity_history_and_intake(
    db_session: Session,
) -> None:
    counts_before = _entity_counts(db_session)
    history_before = db_session.scalar(
        select(func.count()).select_from(OpportunityStatusHistory)
    )
    db_session.rollback()

    def fail_intake_insert(
        _mapper: Mapper[LeadIntake],
        _connection: Connection,
        _target: LeadIntake,
    ) -> None:
        raise RuntimeError("forced intake failure")

    event.listen(LeadIntake, "before_insert", fail_intake_insert)
    try:
        with pytest.raises(RuntimeError, match="forced intake failure"):
            LeadIntakeService(db_session).intake(
                make_intake(external_submission_id="rollback")
            )
    finally:
        event.remove(LeadIntake, "before_insert", fail_intake_insert)

    assert _entity_counts(db_session) == counts_before
    assert (
        db_session.scalar(select(func.count()).select_from(OpportunityStatusHistory))
        == history_before
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" +54 (9) 249-123-4567 ", "+5492491234567"),
        ("11 4444-5555", "1144445555"),
        ("+1-212-555-0100", "+12125550100"),
        ("123-45", None),
        ("  () -  ", None),
        (None, None),
    ],
)
def test_phone_normalization_is_conservative(
    raw: str | None,
    expected: str | None,
) -> None:
    assert comparable_phone(raw) == expected


def test_email_normalization_only_trims_and_lowercases() -> None:
    assert normalize_email(" User+Alias@Example.COM ") == "user+alias@example.com"


def test_concurrent_identical_external_id_creates_once() -> None:
    intake = make_intake(
        external_submission_id=f"concurrent-id-{uuid4().hex}",
        email=f"concurrent-id-{uuid4().hex}@ejemplo.com",
        phone=None,
    )
    barrier = Barrier(2)

    def submit() -> LeadIntakeResult:
        barrier.wait()
        with SessionLocal() as session:
            return LeadIntakeService(session).intake(intake)

    results = _run_concurrently(submit)
    try:
        assert {result.created for result in results} == {False, True}
        assert len({result.intake_id for result in results}) == 1
        assert len({result.opportunity_id for result in results}) == 1
        assert len({result.customer_id for result in results}) == 1
    finally:
        _cleanup_concurrent_results(results)


def test_concurrent_distinct_submissions_with_same_email_share_customer() -> None:
    email = f"concurrent-email-{uuid4().hex}@ejemplo.com"
    inputs = (
        make_intake(external_submission_id=uuid4().hex, email=email, phone=None),
        make_intake(external_submission_id=uuid4().hex, email=email, phone=None),
    )
    barrier = Barrier(2)

    def submit(intake: LeadIntakeInput) -> LeadIntakeResult:
        barrier.wait()
        with SessionLocal() as session:
            return LeadIntakeService(session).intake(intake)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(submit, inputs))
    try:
        assert all(result.created for result in results)
        assert len({result.customer_id for result in results}) == 1
        assert len({result.opportunity_id for result in results}) == 2
    finally:
        _cleanup_concurrent_results(results)


def _entity_counts(db_session: Session) -> tuple[int, int, int]:
    return (
        db_session.scalar(select(func.count()).select_from(Customer)) or 0,
        db_session.scalar(select(func.count()).select_from(Opportunity)) or 0,
        db_session.scalar(select(func.count()).select_from(LeadIntake)) or 0,
    )


def _run_concurrently(
    operation: Callable[[], LeadIntakeResult],
) -> list[LeadIntakeResult]:
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(operation) for _ in range(2)]
        return [future.result() for future in futures]


def _cleanup_concurrent_results(results: list[LeadIntakeResult]) -> None:
    opportunity_ids = {result.opportunity_id for result in results}
    customer_ids = {result.customer_id for result in results}
    with SessionLocal.begin() as session:
        session.execute(text("SET LOCAL asfaltos.test_cleanup = 'on'"))
        session.execute(
            delete(OpportunityStatusHistory).where(
                OpportunityStatusHistory.opportunity_id.in_(opportunity_ids)
            )
        )
        session.execute(
            delete(LeadIntake).where(LeadIntake.opportunity_id.in_(opportunity_ids))
        )
        session.execute(delete(Opportunity).where(Opportunity.id.in_(opportunity_ids)))
        session.execute(delete(Customer).where(Customer.id.in_(customer_ids)))
