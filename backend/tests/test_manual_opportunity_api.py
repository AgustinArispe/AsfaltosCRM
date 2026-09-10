from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models import Customer, Notification, Opportunity, User, UserRole


def test_manual_endpoint_existing_customer_and_idempotent_replay(
    api_client: TestClient,
    db_session: Session,
    supervisor_user: User,
) -> None:
    customer = Customer(name="Cliente API", legendary_historical_override=False)
    db_session.add(customer)
    db_session.commit()
    command_id = str(uuid4())
    payload = {
        "command_id": command_id,
        "assigned_user_id": None,
        "customer": {"kind": "existing", "customer_id": customer.id},
    }

    created = api_client.post("/api/opportunities/manual", json=payload)
    replay = api_client.post("/api/opportunities/manual", json=payload)

    assert created.status_code == 201
    assert created.json()["created"] is True
    assert created.json()["opportunity"]["source"] == "REFERIDO"
    assert created.json()["opportunity"]["status"] == "NUEVA"
    assert created.json()["opportunity"]["history"][0]["changed_by_user_id"] == (
        supervisor_user.id
    )
    assert replay.status_code == 200
    assert replay.json()["created"] is False
    assert replay.json()["opportunity"]["id"] == created.json()["opportunity"]["id"]
    opportunity_id = created.json()["opportunity"]["id"]
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.opportunity_id == opportunity_id)
        )
        == 1
    )


def test_manual_endpoint_creates_new_customer_and_returns_match_conflict(
    api_client: TestClient,
    db_session: Session,
) -> None:
    payload = {
        "command_id": str(uuid4()),
        "customer": {
            "kind": "new",
            "name": "María Referida",
            "company": "Obras del Sur",
            "phone": "+54 9 11 4444-3333",
            "email": "MARIA@EXAMPLE.COM",
            "province": "Buenos Aires",
        },
    }

    created = api_client.post("/api/opportunities/manual", json=payload)

    assert created.status_code == 201
    customer_id = created.json()["opportunity"]["customer"]["id"]
    customer = db_session.get(Customer, customer_id)
    assert customer is not None
    assert customer.email == "maria@example.com"
    assert created.json()["opportunity"]["customer"]["company"] == "Obras del Sur"
    db_session.commit()

    conflict_payload = {
        "command_id": str(uuid4()),
        "customer": {
            "kind": "new",
            "name": "Otro nombre",
            "company": "Obras del Sur",
            "phone": "+54 9 11 4444-3333",
            "email": "MARIA@EXAMPLE.COM",
            "province": "Buenos Aires",
        },
    }
    conflict = api_client.post("/api/opportunities/manual", json=conflict_payload)

    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "MANUAL_CUSTOMER_MATCH_EXISTS"
    assert conflict.json()["detail"]["customer"]["id"] == customer_id


def test_manual_endpoint_rejects_source_status_and_vendor_assignment(
    api_client: TestClient,
    db_session: Session,
) -> None:
    customer = Customer(name="Cliente permisos", legendary_historical_override=False)
    vendor = User(
        full_name="Vendedor manual",
        email="vendor-api-manual@faa.test",
        password_hash=hash_password("vendor-api-password"),
        role=UserRole.VENDEDOR,
    )
    assignee = User(
        full_name="Responsable manual",
        email="assignee-api-manual@faa.test",
        password_hash=hash_password("assignee-api-password"),
        role=UserRole.VENDEDOR,
    )
    db_session.add_all([customer, vendor, assignee])
    db_session.commit()
    initial_opportunity_count = db_session.scalar(
        select(func.count()).select_from(Opportunity)
    )
    db_session.commit()
    api_client.headers["Authorization"] = f"Bearer {create_access_token(vendor.id)}"
    base_payload = {
        "command_id": str(uuid4()),
        "customer": {"kind": "existing", "customer_id": customer.id},
    }

    with_source = api_client.post(
        "/api/opportunities/manual",
        json={**base_payload, "source": "WEB"},
    )
    with_status = api_client.post(
        "/api/opportunities/manual",
        json={**base_payload, "command_id": str(uuid4()), "status": "GANADA"},
    )
    assigned = api_client.post(
        "/api/opportunities/manual",
        json={
            **base_payload,
            "command_id": str(uuid4()),
            "assigned_user_id": assignee.id,
        },
    )

    assert with_source.status_code == 422
    assert with_status.status_code == 422
    assert assigned.status_code == 403
    assert (
        db_session.scalar(select(func.count()).select_from(Opportunity))
        == initial_opportunity_count
    )


def test_manual_endpoint_reports_deleted_identity_code(
    api_client: TestClient,
    db_session: Session,
) -> None:
    deleted = Customer(
        name="Cliente eliminado",
        email="eliminado-api@faa.test",
        deleted_at=datetime.now(UTC) + timedelta(seconds=1),
        legendary_historical_override=False,
    )
    db_session.add(deleted)
    db_session.commit()

    response = api_client.post(
        "/api/opportunities/manual",
        json={
            "command_id": str(uuid4()),
            "customer": {
                "kind": "new",
                "name": "Cliente nuevo",
                "email": "eliminado-api@faa.test",
            },
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == {"code": "MANUAL_CUSTOMER_IDENTITY_DELETED"}
