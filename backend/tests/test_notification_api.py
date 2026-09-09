from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import (
    Customer,
    LeadSource,
    Notification,
    NotificationRecipient,
    NotificationType,
    Opportunity,
    OpportunityStatus,
    User,
    UserRole,
)
from app.schemas import NotificationResponse


def persist(db_session: Session, *entities: object) -> None:
    db_session.add_all(entities)
    db_session.commit()


def make_notification(
    db_session: Session,
    *,
    user_id: int,
    created_at: datetime,
    read: bool = False,
    resolved: bool = False,
) -> Notification:
    customer = Customer(
        name=f"Cliente API notification {uuid4().hex}",
        company="Constructora Notification",
    )
    opportunity = Opportunity(
        customer=customer,
        source=LeadSource.WEB,
        status=OpportunityStatus.COTIZADA,
        current_status_entered_at=created_at - timedelta(days=15),
        created_at=created_at - timedelta(days=20),
        updated_at=created_at - timedelta(days=15),
    )
    notification = Notification(
        type=NotificationType.OPPORTUNITY_STALE,
        opportunity=opportunity,
        created_at=created_at,
        resolved_at=created_at + timedelta(minutes=2) if resolved else None,
    )
    db_session.add(notification)
    db_session.flush()
    db_session.add(
        NotificationRecipient(
            notification_id=notification.id,
            user_id=user_id,
            created_at=created_at,
            read_at=created_at + timedelta(minutes=1) if read else None,
        )
    )
    db_session.commit()
    return notification


def test_notifications_require_authentication(api_client: TestClient) -> None:
    del api_client.headers["Authorization"]
    assert api_client.get("/api/notifications").status_code == 401
    assert api_client.post("/api/notifications/read-all").status_code == 401


def test_list_returns_active_typed_detail_with_stable_pagination_order(
    api_client: TestClient,
    db_session: Session,
    supervisor_user: User,
) -> None:
    created_at = datetime.now(UTC) - timedelta(minutes=5)
    first = make_notification(
        db_session, created_at=created_at, user_id=supervisor_user.id
    )
    second = make_notification(
        db_session, created_at=created_at, user_id=supervisor_user.id
    )
    make_notification(
        db_session, created_at=created_at, resolved=True, user_id=supervisor_user.id
    )

    response = api_client.get(
        "/api/notifications",
        params={"page": 1, "page_size": 2},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["page"] == 1
    assert response.json()["page_size"] == 2
    notifications = [
        NotificationResponse.model_validate(item) for item in response.json()["items"]
    ]
    assert [notification.id for notification in notifications] == [second.id, first.id]
    assert notifications[0].type is NotificationType.OPPORTUNITY_STALE
    assert notifications[0].opportunity.id == second.opportunity_id
    assert notifications[0].opportunity.status is OpportunityStatus.COTIZADA
    assert notifications[0].opportunity.customer.company == (
        "Constructora Notification"
    )


def test_unread_and_resolved_filters(
    api_client: TestClient, db_session: Session, supervisor_user: User
) -> None:
    created_at = datetime.now(UTC) - timedelta(minutes=5)
    unread = make_notification(
        db_session, created_at=created_at, user_id=supervisor_user.id
    )
    make_notification(
        db_session, created_at=created_at, read=True, user_id=supervisor_user.id
    )
    resolved = make_notification(
        db_session, created_at=created_at, resolved=True, user_id=supervisor_user.id
    )

    unread_response = api_client.get(
        "/api/notifications",
        params={"unread_only": True},
    )
    all_response = api_client.get(
        "/api/notifications",
        params={"include_resolved": True},
    )

    assert unread_response.status_code == 200
    assert unread_response.json()["total"] == 1
    assert unread_response.json()["items"][0]["id"] == unread.id
    all_ids = {item["id"] for item in all_response.json()["items"]}
    assert resolved.id in all_ids
    assert all_response.json()["total"] == 3


def test_mark_read_is_idempotent_and_rejects_internal_fields(
    api_client: TestClient,
    db_session: Session,
    supervisor_user: User,
) -> None:
    notification = make_notification(
        db_session,
        created_at=datetime.now(UTC) - timedelta(minutes=5),
        user_id=supervisor_user.id,
    )

    first = api_client.post(f"/api/notifications/{notification.id}/read")
    second = api_client.post(f"/api/notifications/{notification.id}/read")
    forbidden = api_client.post(
        f"/api/notifications/{notification.id}/read",
        json={
            "resolved_at": datetime.now(UTC).isoformat(),
            "type": "OPPORTUNITY_STALE",
            "opportunity_id": notification.opportunity_id,
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["read_at"] == second.json()["read_at"]
    assert first.json()["resolved_at"] is None
    assert forbidden.status_code == 422
    assert api_client.post("/api/notifications/999999999/read").status_code == 404


def test_read_all_marks_only_active_notifications(
    api_client: TestClient,
    db_session: Session,
    supervisor_user: User,
) -> None:
    created_at = datetime.now(UTC) - timedelta(minutes=5)
    active = make_notification(
        db_session, created_at=created_at, user_id=supervisor_user.id
    )
    resolved = make_notification(
        db_session, created_at=created_at, resolved=True, user_id=supervisor_user.id
    )

    response = api_client.post("/api/notifications/read-all")
    all_notifications = api_client.get(
        "/api/notifications",
        params={"include_resolved": True},
    )

    assert response.status_code == 200
    assert response.json() == {"updated_count": 1}
    by_id = {item["id"]: item for item in all_notifications.json()["items"]}
    assert by_id[active.id]["read_at"] is not None
    assert by_id[resolved.id]["read_at"] is None


def test_new_opportunity_notifies_active_users_with_independent_read_state(
    api_client: TestClient,
    db_session: Session,
) -> None:
    seller = User(
        full_name="Vendedora notificada",
        email=f"seller-{uuid4().hex}@faa.test",
        password_hash="hashed-password",
        role=UserRole.VENDEDOR,
    )
    inactive = User(
        full_name="Usuario inactivo",
        email=f"inactive-{uuid4().hex}@faa.test",
        password_hash="hashed-password",
        role=UserRole.VENDEDOR,
        is_active=False,
    )
    customer = Customer(name=f"Lead notification {uuid4().hex}")
    persist(db_session, seller, inactive, customer)
    expected_active_user_ids = set(
        db_session.scalars(select(User.id).where(User.is_active.is_(True)))
    )
    seller_id = seller.id
    inactive_id = inactive.id
    customer_id = customer.id
    db_session.rollback()

    created = api_client.post(
        "/api/opportunities",
        json={"customer_id": customer_id, "source": "WEB"},
    )
    assert created.status_code == 201
    opportunity_id = created.json()["id"]
    notification = db_session.scalar(
        select(Notification).where(
            Notification.opportunity_id == opportunity_id,
            Notification.type == NotificationType.NEW_LEAD,
        )
    )
    assert notification is not None
    recipients = list(
        db_session.scalars(
            select(NotificationRecipient).where(
                NotificationRecipient.notification_id == notification.id
            )
        )
    )
    assert {recipient.user_id for recipient in recipients} == expected_active_user_ids
    assert inactive_id not in expected_active_user_ids
    notification_id = notification.id
    db_session.rollback()

    supervisor_list = api_client.get("/api/notifications", params={"unread_only": True})
    assert supervisor_list.json()["total"] == 1
    assert supervisor_list.json()["items"][0]["type"] == "NEW_LEAD"
    api_client.post(f"/api/notifications/{notification_id}/read")

    api_client.headers["Authorization"] = f"Bearer {create_access_token(seller_id)}"
    seller_list = api_client.get("/api/notifications", params={"unread_only": True})
    assert seller_list.json()["total"] == 1
    assert seller_list.json()["items"][0]["id"] == notification_id
