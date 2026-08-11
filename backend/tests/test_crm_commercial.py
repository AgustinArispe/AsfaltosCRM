from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Never, Self
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.models import (
    Customer,
    CustomerImportAction,
    CustomerImportStatus,
    CustomerLegendaryEvent,
    LeadSource,
    LegendaryEventType,
    LossReason,
    Opportunity,
    OpportunityLossEvent,
    OpportunityNoteRevision,
    OpportunityStatus,
    OpportunityTransitionKind,
    Product,
    User,
    UserRole,
)
from app.scripts import recompute_legendary_customers, smoke_wordpress_intake
from app.services.customer_import_service import CustomerImportService
from app.services.errors import (
    EntityNotFoundError,
    IdempotencyConflictError,
    InvalidCustomerImportError,
    InvalidStateTransitionError,
    RevisionConflictError,
)
from app.services.legendary_service import LegendaryService
from app.services.lost_opportunity_service import LostFilters, LostOpportunityService
from app.services.opportunity_note_service import OpportunityNoteService
from app.services.opportunity_query_service import OpportunityQueryService
from app.services.opportunity_service import OpportunityService, QuoteProductInput


def _actor(db_session: Session, suffix: str) -> User:
    actor = User(
        full_name=f"Actor {suffix}",
        email=f"actor-{suffix}@faa.test",
        password_hash="not-used",
        role=UserRole.SUPERVISOR,
    )
    db_session.add(actor)
    db_session.commit()
    return actor


def _customer(db_session: Session, suffix: str) -> Customer:
    customer = Customer(
        name=f"Cliente {suffix}",
        company=f"Empresa {suffix}",
        email=f"cliente-{suffix}@faa.test",
        phone=f"+54 11 55{suffix[-6:]}",
        province="Buenos Aires",
    )
    db_session.add(customer)
    db_session.commit()
    return customer


def _quoted_negotiation(
    db_session: Session,
    customer: Customer,
    actor: User,
    suffix: str,
) -> tuple[Opportunity, Product]:
    product = Product(name=f"Asfalto {suffix}")
    db_session.add(product)
    db_session.commit()
    service = OpportunityService(db_session)
    opportunity = service.create_opportunity(
        customer_id=customer.id,
        source=LeadSource.WEB,
        changed_by_user_id=actor.id,
    )
    service.quote_opportunity(
        opportunity.id,
        [QuoteProductInput(product.id, Decimal("1250.500"))],
        changed_by_user_id=actor.id,
    )
    service.move_to_negotiation(opportunity.id, changed_by_user_id=actor.id)
    return opportunity, product


def test_notes_are_append_only_searchable_pinned_and_idempotent(
    db_session: Session,
) -> None:
    suffix = uuid4().hex
    actor = _actor(db_session, suffix)
    customer = _customer(db_session, suffix)
    opportunity = OpportunityService(db_session).create_opportunity(
        customer_id=customer.id,
        source=LeadSource.WEB,
        changed_by_user_id=actor.id,
    )
    service = OpportunityNoteService(db_session)
    create_id = uuid4()
    created = service.create(
        opportunity.id,
        command_id=create_id,
        body="  Primera línea\r\nSegunda línea  ",
        is_pinned=False,
        actor_user_id=actor.id,
    )
    replay = service.create(
        opportunity.id,
        command_id=create_id,
        body="Primera línea\nSegunda línea",
        is_pinned=False,
        actor_user_id=actor.id,
    )
    assert replay.current_revision.id == created.current_revision.id
    assert created.current_revision.body == "Primera línea\nSegunda línea"

    revised = service.revise(
        opportunity.id,
        created.id,
        command_id=uuid4(),
        expected_revision=1,
        body="Texto comercial buscable",
        is_pinned=True,
        actor_user_id=actor.id,
    )
    assert revised.current_revision.revision_number == 2
    assert revised.current_revision.is_pinned is True
    second = service.create(
        opportunity.id,
        command_id=uuid4(),
        body="Otra nota",
        is_pinned=False,
        actor_user_id=actor.id,
    )
    first_page = service.list_current(
        opportunity.id,
        search=None,
        pinned=None,
        limit=1,
        cursor=None,
    )
    assert first_page.next_cursor is not None
    second_page = service.list_current(
        opportunity.id,
        search=None,
        pinned=None,
        limit=1,
        cursor=first_page.next_cursor,
    )
    assert [item.id for item in second_page.items] == [second.id]
    page = service.list_current(
        opportunity.id,
        search="comercial",
        pinned=True,
        limit=1,
        cursor=None,
    )
    assert [item.id for item in page.items] == [created.id]
    history = service.list_revisions(opportunity.id, created.id)
    assert [revision.revision_number for revision in history] == [1, 2]
    opportunity_id = opportunity.id
    note_id = created.id
    actor_id = actor.id
    db_session.commit()
    with pytest.raises(RevisionConflictError, match="cursor"):
        service.list_current(
            opportunity_id,
            search=None,
            pinned=None,
            limit=10,
            cursor="invalid",
        )
    db_session.rollback()
    with pytest.raises(RevisionConflictError):
        service.revise(
            opportunity_id,
            note_id,
            command_id=uuid4(),
            expected_revision=1,
            body="stale",
            is_pinned=None,
            actor_user_id=actor_id,
        )
    with pytest.raises(IdempotencyConflictError):
        service.create(
            opportunity_id,
            command_id=create_id,
            body="different",
            is_pinned=False,
            actor_user_id=actor_id,
        )
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(
            update(OpportunityNoteRevision)
            .where(OpportunityNoteRevision.id == history[0].id)
            .values(body="overwrite")
        )


def test_notes_work_in_terminal_states_and_reject_deleted_opportunity(
    db_session: Session,
) -> None:
    suffix = uuid4().hex
    actor = _actor(db_session, suffix)
    customer = _customer(db_session, suffix)
    opportunity, _ = _quoted_negotiation(db_session, customer, actor, suffix)
    OpportunityService(db_session).mark_as_won(
        opportunity.id, changed_by_user_id=actor.id
    )
    note = OpportunityNoteService(db_session).create(
        opportunity.id,
        command_id=uuid4(),
        body="Nota ganada <b>texto, no HTML</b>",
        is_pinned=False,
        actor_user_id=actor.id,
    )
    assert "<b>" in note.current_revision.body
    OpportunityService(db_session).soft_delete_opportunity(opportunity.id)
    with pytest.raises(EntityNotFoundError, match="was not found"):
        OpportunityNoteService(db_session).create(
            opportunity.id,
            command_id=uuid4(),
            body="No debe agregarse",
            is_pinned=False,
            actor_user_id=actor.id,
        )


def test_legendary_calendar_rule_manual_override_and_events(
    db_session: Session,
) -> None:
    suffix = uuid4().hex
    actor = _actor(db_session, suffix)
    customer = _customer(db_session, suffix)
    first_won_created = datetime(2020, 2, 29, 15, tzinfo=UTC)
    won = Opportunity(
        customer_id=customer.id,
        source=LeadSource.WEB,
        status=OpportunityStatus.GANADA,
        created_at=first_won_created,
        updated_at=first_won_created,
        current_status_entered_at=first_won_created,
    )
    db_session.add(won)
    db_session.commit()
    before_anniversary = datetime(2023, 2, 28, 14, 59, tzinfo=UTC)
    before_customer = LegendaryService(db_session).recompute_customer(
        customer.id, evaluated_at=before_anniversary
    )
    assert before_customer.legendary_automatic is False
    eligible_customer = LegendaryService(db_session).recompute_customer(
        customer.id, evaluated_at=datetime(2023, 2, 28, 15, tzinfo=UTC)
    )
    assert eligible_customer.legendary_automatic is True
    assert eligible_customer.is_legendary is True
    events = list(
        db_session.scalars(
            select(CustomerLegendaryEvent).where(
                CustomerLegendaryEvent.customer_id == customer.id
            )
        )
    )
    assert [event.event_type for event in events] == [
        LegendaryEventType.AUTOMATIC_CHANGED
    ]

    db_session.commit()
    with db_session.begin():
        LegendaryService(db_session).record_manual_change_in_transaction(
            customer,
            new_value=True,
            actor_user_id=actor.id,
            occurred_at=datetime.now(UTC),
        )
    won.deleted_at = datetime.now(UTC)
    won.updated_at = won.deleted_at
    db_session.commit()
    LegendaryService(db_session).recompute_customer(customer.id)
    assert customer.legendary_historical_override is True
    assert customer.legendary_automatic is False
    assert customer.is_legendary is True


def test_legendary_batch_validation_and_cli_bounds(db_session: Session) -> None:
    with pytest.raises(ValueError, match="batch_size"):
        LegendaryService(db_session).recompute_batch(
            after_customer_id=0,
            batch_size=0,
            evaluated_at=datetime.now(UTC),
        )
    assert recompute_legendary_customers.main(["--batch-size", "0"]) == 2
    assert recompute_legendary_customers.main(["--now", "2026-01-01"]) == 2
    assert (
        recompute_legendary_customers.main(
            [
                "--batch-size",
                "10",
                "--max-batches",
                "1",
                "--now",
                "2026-08-11T12:00:00+00:00",
            ]
        )
        == 0
    )


def test_loss_workspace_reopen_reloss_and_snapshots(db_session: Session) -> None:
    suffix = uuid4().hex
    actor = _actor(db_session, suffix)
    customer = _customer(db_session, suffix)
    opportunity, product = _quoted_negotiation(db_session, customer, actor, suffix)
    service = OpportunityService(db_session)
    service.mark_as_lost(
        opportunity.id,
        LossReason.PRECIO,
        changed_by_user_id=actor.id,
    )
    assert (
        OpportunityQueryService(db_session).list_opportunities(
            page=1,
            page_size=100,
            status=None,
            customer_id=customer.id,
            assigned_user_id=None,
            source=None,
        )[1]
        == 0
    )
    lost_service = LostOpportunityService(db_session)
    filters = LostFilters(
        search=customer.company,
        reasons=(LossReason.PRECIO,),
        customer_id=customer.id,
        province=" buenos aires ",
        product_id=product.id,
        source=LeadSource.WEB,
        lost_from=datetime.now(UTC) - timedelta(days=1),
        lost_to=datetime.now(UTC) + timedelta(days=1),
    )
    page = lost_service.list_current(filters, limit=10, cursor=None)
    assert len(page.items) == 1
    assert page.items[0].quoted_total_kg == Decimal("1250.500")
    stats = lost_service.statistics(filters)
    assert stats.current_count == 1
    assert stats.historical_loss_count == 1
    assert stats.by_product[0].product_name == product.name

    db_session.commit()
    command_id = uuid4()
    reopened = service.reopen(
        opportunity.id,
        command_id=command_id,
        expected_status=OpportunityStatus.PERDIDA,
        changed_by_user_id=actor.id,
    )
    replay = service.reopen(
        opportunity.id,
        command_id=command_id,
        expected_status=OpportunityStatus.PERDIDA,
        changed_by_user_id=actor.id,
    )
    assert reopened.status is OpportunityStatus.NEGOCIACION
    assert replay.id == reopened.id
    detail = OpportunityQueryService(db_session).get_detail(opportunity.id)
    assert detail.is_reopened is True
    assert detail.reopen_count == 1
    assert detail.loss_reason is None
    assert (
        detail.status_history[-1].transition_kind is OpportunityTransitionKind.REOPENED
    )
    assert lost_service.statistics(filters).reopened_count == 1

    db_session.commit()
    service.mark_as_lost(
        opportunity.id,
        LossReason.COMPETENCIA,
        changed_by_user_id=actor.id,
    )
    episodes = list(
        db_session.scalars(
            select(OpportunityLossEvent)
            .where(OpportunityLossEvent.opportunity_id == opportunity.id)
            .order_by(OpportunityLossEvent.id)
        )
    )
    assert [episode.reason for episode in episodes] == [
        LossReason.PRECIO,
        LossReason.COMPETENCIA,
    ]
    assert (
        lost_service.statistics(
            LostFilters(customer_id=customer.id)
        ).historical_loss_count
        == 2
    )


def test_reopen_requires_lost_status_and_retained_quote(db_session: Session) -> None:
    suffix = uuid4().hex
    actor = _actor(db_session, suffix)
    customer = _customer(db_session, suffix)
    opportunity = OpportunityService(db_session).create_opportunity(
        customer_id=customer.id,
        source=LeadSource.WEB,
        changed_by_user_id=actor.id,
    )
    with pytest.raises(InvalidStateTransitionError):
        OpportunityService(db_session).reopen(
            opportunity.id,
            command_id=uuid4(),
            expected_status=OpportunityStatus.PERDIDA,
            changed_by_user_id=actor.id,
        )


def test_customer_import_preview_commit_replay_and_stale_rollback(
    db_session: Session,
) -> None:
    suffix = uuid4().hex
    actor = _actor(db_session, suffix)
    existing = Customer(
        name=f"Existente {suffix}",
        email=f"existing-{suffix}@faa.test",
    )
    unchanged = Customer(
        name=f"Sin cambios {suffix}",
        company="Completa",
        email=f"unchanged-{suffix}@faa.test",
        province="Córdoba",
    )
    db_session.add_all([existing, unchanged])
    db_session.commit()
    content = (
        "name,company,email,phone,province\n"
        f"Nuevo {suffix},Nueva SA,new-{suffix}@faa.test,,Mendoza\n"
        f"Existente {suffix},Enriquecida,existing-{suffix}@faa.test,,Santa Fe\n"
        f"Sin cambios {suffix},Completa,unchanged-{suffix}@faa.test,,Córdoba\n"
    ).encode()
    service = CustomerImportService(db_session)
    batch = service.dry_run(
        client_import_id=uuid4(),
        filename="../../clientes.csv",
        content=content,
        actor_user_id=actor.id,
    )
    assert batch.status is CustomerImportStatus.VALID
    assert batch.source_filename == "clientes.csv"
    assert [row.action for row in batch.rows] == [
        CustomerImportAction.CREATE,
        CustomerImportAction.ENRICH,
        CustomerImportAction.UNCHANGED,
    ]
    commit_id = uuid4()
    result = service.commit(
        batch.id,
        command_id=commit_id,
        expected_version=1,
        file_sha256=batch.file_sha256,
        actor_user_id=actor.id,
    )
    assert (result.created_count, result.enriched_count, result.unchanged_count) == (
        1,
        1,
        1,
    )
    assert len(result.customer_ids) == 3
    assert existing.company == "Enriquecida"
    replay = service.commit(
        batch.id,
        command_id=commit_id,
        expected_version=1,
        file_sha256=batch.file_sha256,
        actor_user_id=actor.id,
    )
    assert replay.customer_ids == result.customer_ids

    stale_content = (
        "name,company,email,phone,province\n"
        f"Stale {suffix},,stale-{suffix}@faa.test,,\n"
    ).encode()
    stale = service.dry_run(
        client_import_id=uuid4(),
        filename="stale.csv",
        content=stale_content,
        actor_user_id=actor.id,
    )
    db_session.add(Customer(name="Concurrent", email=f"stale-{suffix}@faa.test"))
    db_session.commit()
    before = db_session.scalar(select(func.count(Customer.id)))
    db_session.commit()
    with pytest.raises(InvalidCustomerImportError):
        service.commit(
            stale.id,
            command_id=uuid4(),
            expected_version=1,
            file_sha256=stale.file_sha256,
            actor_user_id=actor.id,
        )
    assert db_session.scalar(select(func.count(Customer.id))) == before


@pytest.mark.parametrize(
    ("content", "expected_status"),
    [
        (b"bad,header\nvalue,row\n", CustomerImportStatus.INVALID),
        (b"name,company,email,phone,province\n", CustomerImportStatus.INVALID),
        (
            b"name,company,email,phone,province\nA,,same@test.com,,\nB,,same@test.com,,\n",
            CustomerImportStatus.INVALID,
        ),
        (b"\xff\xfe", CustomerImportStatus.INVALID),
        (
            b'name,company,email,phone,province\n"unclosed,,,,',
            CustomerImportStatus.INVALID,
        ),
        (
            b"name,company,email,phone,province\nMissing columns,only\n",
            CustomerImportStatus.INVALID,
        ),
        (
            b"name,company,email,phone,province\n,,bad email,123,\n",
            CustomerImportStatus.INVALID,
        ),
    ],
)
def test_customer_import_reports_invalid_files(
    db_session: Session,
    content: bytes,
    expected_status: CustomerImportStatus,
) -> None:
    actor = _actor(db_session, uuid4().hex)
    actor_id = actor.id
    service = CustomerImportService(db_session)
    import_id = uuid4()
    batch = service.dry_run(
        client_import_id=import_id,
        filename="input.csv",
        content=content,
        actor_user_id=actor_id,
    )
    assert batch.status is expected_status
    assert batch.error_count > 0
    batch_id = batch.id
    digest = batch.file_sha256
    with pytest.raises(InvalidCustomerImportError):
        service.commit(
            batch_id,
            command_id=uuid4(),
            expected_version=1,
            file_sha256=digest,
            actor_user_id=actor_id,
        )
    with pytest.raises(IdempotencyConflictError):
        service.dry_run(
            client_import_id=import_id,
            filename="changed.csv",
            content=b"different",
            actor_user_id=actor_id,
        )


def test_wordpress_smoke_requires_explicit_safe_production_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("WEB_INTAKE_SIGNING_SECRET", raising=False)
    assert (
        smoke_wordpress_intake.main(
            [
                "--endpoint",
                "http://localhost/api/intake/web",
                "--confirm-production",
                "no",
            ]
        )
        == 2
    )
    assert (
        smoke_wordpress_intake.main(
            [
                "--endpoint",
                "https://crm.example.com/api/intake/web",
                "--confirm-production",
                smoke_wordpress_intake.CONFIRMATION,
            ]
        )
        == 2
    )

    class FakeResponse:
        status = 201

        def __enter__(self) -> Self:
            return self

        def __exit__(
            self,
            exception_type: object,
            exception: object,
            traceback: object,
        ) -> None:
            del exception_type, exception, traceback

        def read(self) -> bytes:
            return b'{"intake_id":1,"customer_id":2,"opportunity_id":3,"created":true}'

    def successful_urlopen(request: object, *, timeout: int) -> FakeResponse:
        del request, timeout
        return FakeResponse()

    monkeypatch.setenv("WEB_INTAKE_SIGNING_SECRET", "x" * 32)
    monkeypatch.setattr(smoke_wordpress_intake, "urlopen", successful_urlopen)
    assert (
        smoke_wordpress_intake.main(
            [
                "--endpoint",
                "https://crm.example.com/api/intake/web",
                "--confirm-production",
                smoke_wordpress_intake.CONFIRMATION,
            ]
        )
        == 0
    )

    def failed_urlopen(request: object, *, timeout: int) -> Never:
        del request, timeout
        raise TimeoutError

    monkeypatch.setattr(smoke_wordpress_intake, "urlopen", failed_urlopen)
    assert (
        smoke_wordpress_intake.main(
            [
                "--endpoint",
                "https://crm.example.com/api/intake/web",
                "--confirm-production",
                smoke_wordpress_intake.CONFIRMATION,
            ]
        )
        == 1
    )


def test_crm_commercial_api_contracts(
    db_session: Session,
    api_client: TestClient,
    supervisor_user: User,
) -> None:
    suffix = uuid4().hex
    customer = _customer(db_session, suffix)
    opportunity, product = _quoted_negotiation(
        db_session, customer, supervisor_user, suffix
    )
    OpportunityService(db_session).mark_as_lost(
        opportunity.id,
        LossReason.OTRO,
        changed_by_user_id=supervisor_user.id,
    )

    note_command = uuid4()
    created_note = api_client.post(
        f"/api/opportunities/{opportunity.id}/notes",
        json={
            "client_generated_id": str(note_command),
            "body": "Seguimiento interno",
            "is_pinned": False,
        },
    )
    assert created_note.status_code == 201
    note_id = created_note.json()["id"]
    revised_note = api_client.post(
        f"/api/opportunities/{opportunity.id}/notes/{note_id}/revisions",
        json={
            "command_id": str(uuid4()),
            "expected_revision": 1,
            "is_pinned": True,
        },
    )
    assert revised_note.status_code == 200
    assert revised_note.json()["current_revision"]["revision_number"] == 2
    notes = api_client.get(
        f"/api/opportunities/{opportunity.id}/notes",
        params={"search": "Seguimiento", "pinned": "true"},
    )
    assert notes.status_code == 200
    assert len(notes.json()["items"]) == 1
    revisions = api_client.get(
        f"/api/opportunities/{opportunity.id}/notes/{note_id}/revisions"
    )
    assert len(revisions.json()) == 2

    lost = api_client.get(
        "/api/lost-opportunities",
        params={
            "reason": "OTRO",
            "customer_id": customer.id,
            "product_id": product.id,
        },
    )
    assert lost.status_code == 200
    assert lost.json()["items"][0]["opportunity"]["id"] == opportunity.id
    statistics = api_client.get(
        "/api/lost-opportunities/statistics",
        params={"customer_id": customer.id},
    )
    assert statistics.status_code == 200
    assert statistics.json()["historical_loss_count"] == 1
    reopened = api_client.post(
        f"/api/opportunities/{opportunity.id}/reopen",
        json={
            "command_id": str(uuid4()),
            "expected_status": "PERDIDA",
        },
    )
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "NEGOCIACION"
    assert reopened.json()["is_reopened"] is True

    import_id = uuid4()
    csv_content = (
        "name,company,email,phone,province\n"
        f"API Import {suffix},,api-import-{suffix}@faa.test,,Salta\n"
    ).encode()
    preview = api_client.post(
        "/api/customer-imports/dry-run",
        data={"client_import_id": str(import_id)},
        files={"file": ("customers.csv", csv_content, "text/csv")},
    )
    assert preview.status_code == 201
    report = preview.json()
    assert report["status"] == "VALID"
    fetched = api_client.get(f"/api/customer-imports/{report['id']}")
    assert fetched.status_code == 200
    committed = api_client.post(
        f"/api/customer-imports/{report['id']}/commit",
        json={
            "command_id": str(uuid4()),
            "expected_version": report["version"],
            "file_sha256": report["file_sha256"],
        },
    )
    assert committed.status_code == 200
    assert committed.json()["created_count"] == 1
