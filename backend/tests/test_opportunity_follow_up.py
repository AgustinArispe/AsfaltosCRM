from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import (
    Customer,
    LeadSource,
    Notification,
    NotificationType,
    Opportunity,
    OpportunityStatus,
    User,
    UserRole,
)
from app.services.errors import StaleWriteConflictError
from app.services.notification_service import NotificationService
from app.services.opportunity_service import OpportunityService


def overdue(session: Session) -> Opportunity:
    entered = datetime.now(UTC) - timedelta(days=10)
    item = Opportunity(
        customer=Customer(name=f"Seguimiento {uuid4().hex}"),
        source=LeadSource.WEB,
        status=OpportunityStatus.NUEVA,
        created_at=entered,
        updated_at=entered,
        current_status_entered_at=entered,
    )
    session.add(item)
    session.commit()
    return item


def test_follow_up_clears_stale_notices_preserves_stage_and_rearms_at_seven_days(
    api_client: TestClient,
    db_session: Session,
    supervisor_user: User,
) -> None:
    item = overdue(db_session)
    item_id = item.id
    entered = item.current_status_entered_at
    now = datetime.now(UTC)
    service = NotificationService(db_session)
    assert (
        service.generate_stale_opportunity_notifications(now=now, threshold_days=7) == 1
    )
    before = api_client.get(f"/api/opportunities/{item_id}").json()
    payload = {"expected_follow_up_since": before["follow_up_since"]}
    response = api_client.post(f"/api/opportunities/{item_id}/follow-up", json=payload)
    assert response.status_code == 200
    detail = response.json()
    assert detail["status"] == before["status"]
    assert detail["current_status_entered_at"] == before["current_status_entered_at"]
    assert detail["history"] == before["history"]
    assert detail["products"] == before["products"]
    assert detail["follow_up_since"] == detail["last_followed_up_at"]
    followed_at = datetime.fromisoformat(
        detail["last_followed_up_at"].replace("Z", "+00:00")
    )
    replay = api_client.post(f"/api/opportunities/{item_id}/follow-up", json=payload)
    assert replay.status_code == 200
    assert replay.json()["last_followed_up_at"] == detail["last_followed_up_at"]
    assert (
        api_client.get(f"/api/opportunities/{item_id}").json()["last_followed_up_at"]
        == detail["last_followed_up_at"]
    )
    persisted = db_session.get(Opportunity, item_id)
    assert persisted is not None
    assert persisted.last_followed_up_by_user_id == supervisor_user.id
    notice = db_session.scalar(
        select(Notification).where(Notification.opportunity_id == item_id)
    )
    assert notice is not None and notice.resolved_at is not None
    assert persisted.current_status_entered_at == entered
    db_session.commit()
    assert (
        service.generate_stale_opportunity_notifications(
            now=followed_at + timedelta(days=7) - timedelta(microseconds=1),
            threshold_days=7,
        )
        == 0
    )
    assert (
        service.generate_stale_opportunity_notifications(
            now=followed_at + timedelta(days=7), threshold_days=7
        )
        == 1
    )


def test_both_roles_can_follow_up_but_stale_other_actor_cannot_overwrite(
    api_client: TestClient,
    db_session: Session,
    supervisor_user: User,
) -> None:
    item = overdue(db_session)
    item_id = item.id
    baseline = item.current_status_entered_at.isoformat()
    vendor = User(
        full_name="Seguimiento vendedor",
        email=f"{uuid4().hex}@faa.test",
        password_hash="not-used",
        role=UserRole.VENDEDOR,
    )
    db_session.add(vendor)
    db_session.commit()
    api_client.headers["Authorization"] = f"Bearer {create_access_token(vendor.id)}"
    path = f"/api/opportunities/{item_id}/follow-up"
    response = api_client.post(path, json={"expected_follow_up_since": baseline})
    assert response.status_code == 200
    api_client.headers["Authorization"] = (
        f"Bearer {create_access_token(supervisor_user.id)}"
    )
    assert (
        api_client.post(path, json={"expected_follow_up_since": baseline}).status_code
        == 409
    )
    assert (
        api_client.get(f"/api/opportunities/{item_id}").json()["last_followed_up_at"]
        == response.json()["last_followed_up_at"]
    )


@pytest.mark.parametrize("state", ["fresh", "closed", "deleted"])
def test_ineligible_opportunities_do_not_change_follow_up(
    api_client: TestClient,
    db_session: Session,
    state: str,
) -> None:
    item = overdue(db_session)
    if state == "fresh":
        item.current_status_entered_at = datetime.now(UTC)
    elif state == "closed":
        item.status = OpportunityStatus.GANADA
    else:
        item.deleted_at = datetime.now(UTC)
    db_session.commit()
    response = api_client.post(
        f"/api/opportunities/{item.id}/follow-up",
        json={"expected_follow_up_since": item.follow_up_since.isoformat()},
    )
    assert response.status_code == (404 if state == "deleted" else 409)
    db_session.refresh(item)
    assert item.last_followed_up_at is None


def test_follow_up_validates_aware_baseline_and_does_not_resolve_new_lead_notifications(
    api_client: TestClient,
    db_session: Session,
) -> None:
    item = overdue(db_session)
    item_id = item.id
    baseline = item.follow_up_since.isoformat()
    notice = Notification(opportunity_id=item.id, type=NotificationType.NEW_LEAD)
    db_session.add(notice)
    db_session.commit()
    path = f"/api/opportunities/{item_id}/follow-up"
    assert api_client.post(path, json={}).status_code == 422
    assert (
        api_client.post(
            path, json={"expected_follow_up_since": "2026-01-01T00:00:00"}
        ).status_code
        == 422
    )
    assert (
        api_client.post(path, json={"expected_follow_up_since": baseline}).status_code
        == 200
    )
    db_session.refresh(notice)
    assert notice.resolved_at is None


def test_new_stage_does_not_replay_an_old_follow_up_request(
    db_session: Session,
    supervisor_user: User,
) -> None:
    item = overdue(db_session)
    item_id, baseline = item.id, item.follow_up_since
    service = OpportunityService(db_session)
    service.follow_up(
        item_id, expected_follow_up_since=baseline, actor_user_id=supervisor_user.id
    )
    service.prepare_quote(
        item_id, note="Nueva etapa", changed_by_user_id=supervisor_user.id
    )
    with pytest.raises(StaleWriteConflictError):
        service.follow_up(
            item_id, expected_follow_up_since=baseline, actor_user_id=supervisor_user.id
        )
