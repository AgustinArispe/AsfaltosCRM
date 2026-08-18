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


def test_visual_qa_seed_refuses_test_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENVIRONMENT", "test")
    get_app_environment.cache_clear()
    try:
        with pytest.raises(SystemExit, match="APP_ENVIRONMENT=development"):
            _guard_runtime()
    finally:
        get_app_environment.cache_clear()


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


def test_visual_qa_cli_creates_dataset_in_development(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENVIRONMENT", "development")
    monkeypatch.setenv("WHATSAPP_PROVIDER", "fake")
    monkeypatch.setenv("QA_SUPERVISOR_PASSWORD", "visual-qa-supervisor-password")
    monkeypatch.setenv("QA_SELLER_PASSWORD", "visual-qa-seller-password")
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
