import sys
from collections import Counter
from contextlib import nullcontext
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import clear_runtime_settings_caches, get_app_environment
from app.models import Customer, Opportunity, OpportunityStatus, Product, User
from app.models.whatsapp_broadcast import WhatsAppBroadcast
from app.models.whatsapp_conversation import WhatsAppConversation
from app.scripts import seed_visual_qa
from app.scripts.seed_visual_qa import (
    CUSTOMERS,
    OPPORTUNITIES,
    PRODUCT_NAMES,
    _guard_runtime,
    _parse_anchor,
    _reset_owned_dataset,
    _seed_dataset,
    _stable_uuid,
)
from app.whatsapp.runtime import development_fake_templates


def test_visual_qa_fixture_covers_current_operational_surfaces() -> None:
    statuses = Counter(item.status for item in OPPORTUNITIES)

    assert statuses[OpportunityStatus.NUEVA] >= 4
    assert statuses[OpportunityStatus.COTIZADA] >= 4
    assert statuses[OpportunityStatus.NEGOCIACION] >= 4
    assert statuses[OpportunityStatus.GANADA] >= 4
    assert statuses[OpportunityStatus.PERDIDA] >= 4
    assert any(item.reopen for item in OPPORTUNITIES)
    assert len(PRODUCT_NAMES) >= 6
    assert len(CUSTOMERS) >= 12
    assert len({item.province for item in CUSTOMERS if item.province}) >= 5


def test_visual_qa_identifiers_and_fake_templates_are_deterministic() -> None:
    assert _stable_uuid("example") == _stable_uuid("example")
    assert _stable_uuid("example") != _stable_uuid("another")
    templates = development_fake_templates()
    assert {template.external_id for template in templates} == {
        "qa-follow-up",
        "qa-delivery",
        "qa-marketing",
    }
    assert all(template.status == "APPROVED" for template in templates)


def test_visual_qa_anchor_requires_timezone_and_normalizes_to_utc() -> None:
    assert _parse_anchor("2026-08-18T12:00:00-03:00") == datetime(
        2026, 8, 18, 15, tzinfo=UTC
    )
    with pytest.raises(SystemExit):
        seed_visual_qa.build_parser().parse_args(["--anchor", "2026-08-18T12:00:00"])


def test_visual_qa_seed_refuses_test_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENVIRONMENT", "test")
    get_app_environment.cache_clear()
    try:
        with pytest.raises(SystemExit, match="APP_ENVIRONMENT=development"):
            _guard_runtime()
    finally:
        get_app_environment.cache_clear()


@pytest.mark.parametrize(
    ("environment_name", "provider_name", "database_url", "expected_message"),
    [
        (
            "production",
            "fake",
            "postgresql+psycopg://asfaltos:test@localhost/asfaltos_crm",
            "APP_ENVIRONMENT=development",
        ),
        (
            "development",
            "meta",
            "postgresql+psycopg://asfaltos:test@localhost/asfaltos_crm",
            "WHATSAPP_PROVIDER=fake",
        ),
        (
            "development",
            "fake",
            "postgresql+psycopg://asfaltos:test@localhost/not_visual_qa",
            "canonical asfaltos_crm database",
        ),
    ],
)
def test_visual_qa_seed_preserves_runtime_provider_and_database_guards(
    monkeypatch: pytest.MonkeyPatch,
    environment_name: str,
    provider_name: str,
    database_url: str,
    expected_message: str,
) -> None:
    monkeypatch.setenv("APP_ENVIRONMENT", environment_name)
    monkeypatch.setenv("WHATSAPP_PROVIDER", provider_name)
    monkeypatch.setenv("DATABASE_URL", database_url)
    clear_runtime_settings_caches()
    try:
        with pytest.raises(SystemExit, match=expected_message):
            _guard_runtime()
    finally:
        clear_runtime_settings_caches()


def test_visual_qa_dataset_is_valid_against_current_schema(db_session: Session) -> None:
    _seed_dataset(
        db_session,
        supervisor_password="visual-qa-supervisor-password",
        seller_password="visual-qa-seller-password",
        anchor=datetime(2026, 8, 18, 12, tzinfo=UTC),
    )

    assert db_session.scalar(select(func.count()).select_from(User)) == 2
    assert db_session.scalar(select(func.count()).select_from(Product)) == 9
    assert db_session.scalar(select(func.count()).select_from(Customer)) == 16
    assert db_session.scalar(select(func.count()).select_from(Opportunity)) == 22
    assert (
        db_session.scalar(select(func.count()).select_from(WhatsAppConversation)) == 10
    )
    assert db_session.scalar(select(func.count()).select_from(WhatsAppBroadcast)) == 3


def test_visual_qa_reset_accepts_formatted_and_normalized_fixture_phones(
    db_session: Session,
) -> None:
    _seed_dataset(
        db_session,
        supervisor_password="visual-qa-supervisor-password",
        seller_password="visual-qa-seller-password",
        anchor=datetime(2026, 8, 18, 12, tzinfo=UTC),
    )

    phones = set(db_session.scalars(select(WhatsAppConversation.external_phone)))
    assert any(" " in phone for phone in phones)
    assert any(" " not in phone for phone in phones)

    _reset_owned_dataset(db_session)

    assert db_session.scalar(select(func.count()).select_from(User)) == 0
    assert db_session.scalar(select(func.count()).select_from(Customer)) == 0
    assert (
        db_session.scalar(select(func.count()).select_from(WhatsAppConversation)) == 0
    )


def test_visual_qa_reset_accepts_exact_browser_qa_roots(db_session: Session) -> None:
    _seed_dataset(
        db_session,
        supervisor_password="visual-qa-supervisor-password",
        seller_password="visual-qa-seller-password",
        anchor=datetime(2026, 8, 18, 12, tzinfo=UTC),
    )
    user = db_session.scalar(select(User).where(User.email == "qa.supervisor@faa.test"))
    products = list(db_session.scalars(select(Product).limit(2)))
    customer = db_session.scalar(select(Customer).limit(1))
    broadcast = db_session.scalar(select(WhatsAppBroadcast).limit(1))
    assert user is not None and len(products) == 2
    assert customer is not None and broadcast is not None
    user.email = "usuario.crm026@faa.test"
    products[0].name = "Producto CRM-026"
    products[1].name = "Producto CRM-026 editado"
    customer.name = "Cliente CRM-026"
    broadcast.label = "Validación CRM-026"
    db_session.commit()

    _reset_owned_dataset(db_session)

    assert db_session.scalar(select(func.count()).select_from(User)) == 0
    assert db_session.scalar(select(func.count()).select_from(Customer)) == 0


def test_visual_qa_reset_refuses_unknown_phone_without_mutation(
    db_session: Session,
) -> None:
    _seed_dataset(
        db_session,
        supervisor_password="visual-qa-supervisor-password",
        seller_password="visual-qa-seller-password",
        anchor=datetime(2026, 8, 18, 12, tzinfo=UTC),
    )
    conversation = db_session.scalar(select(WhatsAppConversation).limit(1))
    assert conversation is not None
    conversation.external_phone = "+5491100000000"
    conversation.phone_match_key = "+5491100000000"
    db_session.commit()

    with pytest.raises(SystemExit, match="roots not owned"):
        _reset_owned_dataset(db_session)

    assert db_session.scalar(select(func.count()).select_from(User)) == 2
    assert db_session.scalar(select(func.count()).select_from(Customer)) == 16
    assert (
        db_session.scalar(select(func.count()).select_from(WhatsAppConversation)) == 10
    )


def test_visual_qa_cli_creates_dataset_in_development(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENVIRONMENT", "development")
    monkeypatch.setenv("WHATSAPP_PROVIDER", "fake")
    monkeypatch.setenv("QA_SUPERVISOR_PASSWORD", "visual-qa-supervisor-password")
    monkeypatch.setenv("QA_SELLER_PASSWORD", "visual-qa-seller-password")
    monkeypatch.setattr(
        seed_visual_qa,
        "get_database_url",
        lambda: "postgresql+psycopg://asfaltos:test@db:5432/asfaltos_crm",
    )
    monkeypatch.setattr(sys, "argv", ["seed_visual_qa"])
    monkeypatch.setattr(
        seed_visual_qa,
        "SessionLocal",
        lambda: nullcontext(db_session),
    )
    clear_runtime_settings_caches()
    try:
        assert seed_visual_qa.main() == 0
        assert seed_visual_qa.main() == 0
    finally:
        clear_runtime_settings_caches()

    assert db_session.scalar(select(func.count()).select_from(Opportunity)) == 22
