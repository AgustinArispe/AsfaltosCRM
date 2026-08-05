from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.models import (
    Customer,
    LeadSource,
    Notification,
    Opportunity,
    OpportunityStatus,
)
from app.scripts import generate_notifications


def test_cli_generates_idempotently_and_returns_zero(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    entered_at = datetime.now(UTC) - timedelta(days=20_000)
    with SessionLocal.begin() as setup_session:
        customer = Customer(name=f"Cliente CLI {uuid4().hex}")
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

    monkeypatch.setattr(
        generate_notifications,
        "get_stale_opportunity_days",
        lambda: 10_000,
    )
    try:
        first_exit_code = generate_notifications.main()
        second_exit_code = generate_notifications.main()
        output = capsys.readouterr().out
        with SessionLocal() as verification_session:
            notification_ids = list(
                verification_session.scalars(
                    select(Notification.id).where(
                        Notification.opportunity_id == opportunity_id
                    )
                )
            )

        assert first_exit_code == 0
        assert second_exit_code == 0
        assert len(notification_ids) == 1
        assert "Created 1 stale opportunity notifications" in output
        assert "Created 0 stale opportunity notifications" in output
    finally:
        with SessionLocal.begin() as cleanup_session:
            cleanup_session.execute(
                delete(Notification).where(
                    Notification.opportunity_id == opportunity_id
                )
            )
            cleanup_session.execute(
                delete(Opportunity).where(Opportunity.id == opportunity_id)
            )
            cleanup_session.execute(delete(Customer).where(Customer.id == customer_id))
